"""
nail_wear_v8_two_stage.py — 两阶段美甲试戴
=========================================
阶段A: 手指属性对齐 (thumb→thumb, index→index, ...)
       先用方向角度旋转，再用DIP定位，不调整根部
阶段B: 根部线微调 (根部边重合)
       在阶段A基础上，用minAreaRect根部中点做精确对齐

步骤:
  Step1:  SAM3 分割 style a2 → 5个RGBA美甲
  Step2:  MediaPipe 检测 a2_natural → 21位点 + DIP→TIP方向
  Step3:  拓扑法标注手指类型 → SAM3轮廓+属性图
  Step3b: SAM3 分割 hand a13 → 轮廓+属性图
  Step4:  MediaPipe 检测 hand a13 → 21位点 + DIP→TIP方向
  Step5:  [阶段A] 手指属性对齐 → 旋转+DIP定位 → rough result
  Step6:  minAreaRect 找根部边 (style + hand)
  Step7:  [阶段B] 根部线微调 → base_mid重合 → final result

用法: python E:\meijia\nail_wear_v8_two_stage.py
(不修改 nail_wear_v7.py)
"""

import cv2, numpy as np, math, os
from pathlib import Path
from ultralytics.models.sam import SAM3SemanticPredictor
import mediapipe as mp
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision

SAM3_WT = r"E:\meijia\model\sam3.pt"
LM = r"E:\meijia\model\hand_landmarker.task"
OUT = r"E:\meijia\model\output"
os.makedirs(OUT, exist_ok=True)

F_DIP = [3,7,11,15,19]; F_TIP = [4,8,12,16,20]
NAMES = ["thumb","index","middle","ring","pinky"]
COLS = {"thumb":(0,255,0),"index":(255,0,0),"middle":(0,0,255),"ring":(255,0,255),"pinky":(0,255,255)}
CONNS = [(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),(0,9),(9,10),(10,11),(11,12),(0,13),(13,14),(14,15),(15,16),(0,17),(17,18),(18,19),(19,20),(5,9),(9,13),(13,17)]

def lk_angle(x1,y1,x2,y2):
    dx=x2-x1; dy=y2-y1; L=math.sqrt(dx**2+dy**2)
    if L==0: return 0.0
    deg=math.degrees(math.asin(abs(dy)/L))
    if dx>0 and dy<0: return deg
    elif dx<0 and dy<0: return 180-deg
    elif dx<0 and dy>0: return 180+deg
    else: return 360-deg

def mp_detect(img_bgr):
    h,w=img_bgr.shape[:2]; rgb=cv2.cvtColor(img_bgr,cv2.COLOR_BGR2RGB)
    mp_img=mp.Image(image_format=mp.ImageFormat.SRGB,data=rgb)
    for conf in [0.3,0.2,0.1,0.05]:
        opt=vision.HandLandmarkerOptions(base_options=mpt.BaseOptions(model_asset_path=LM),num_hands=2,min_hand_detection_confidence=conf)
        det=vision.HandLandmarker.create_from_options(opt); res=det.detect(mp_img); det.close()
        if res and res.hand_landmarks:
            hand=res.hand_landmarks[0]; dirs={}
            for fn,di,ti in zip(NAMES,F_DIP,F_TIP):
                tx=int(hand[ti].x*w); ty=int(hand[ti].y*h); dx=int(hand[di].x*w); dy=int(hand[di].y*h)
                dirs[fn]={"tip":(tx,ty),"dip":(dx,dy),"angle":round(lk_angle(dx,dy,tx,ty),1)}
            return dirs,hand
    return None,None

def draw_21kp(img,hand,dirs,out_path,title=""):
    h,w=img.shape[:2]; vis=img.copy()
    if title: cv2.putText(vis,title,(10,30),cv2.FONT_HERSHEY_SIMPLEX,0.7,(255,255,255),2)
    for a,b in CONNS: cv2.line(vis,(int(hand[a].x*w),int(hand[a].y*h)),(int(hand[b].x*w),int(hand[b].y*h)),(180,180,180),1)
    for i in range(21): pt=(int(hand[i].x*w),int(hand[i].y*h)); cv2.circle(vis,pt,3,(200,200,200),-1)
    for fn in NAMES:
        d=dirs[fn]; c=COLS[fn]; L=math.sqrt((d['tip'][0]-d['dip'][0])**2+(d['tip'][1]-d['dip'][1])**2) or 1
        ext=(int(d['tip'][0]+(d['tip'][0]-d['dip'][0])/L*60),int(d['tip'][1]+(d['tip'][1]-d['dip'][1])/L*60))
        cv2.arrowedLine(vis,d['dip'],ext,c,2,tipLength=0.3); cv2.circle(vis,d['dip'],5,(0,255,255),-1); cv2.circle(vis,d['tip'],6,(0,0,255),-1)
        cv2.putText(vis,f"{fn} {d['angle']}°",(d['tip'][0]+8,d['tip'][1]),cv2.FONT_HERSHEY_SIMPLEX,0.45,c,1)
    cv2.imwrite(out_path,vis)

def get_base_edge(mask_bin, dip_pt, tip_pt=None):
    """
    根部边 = minAreaRect 4条边中满足以下条件的边：
      (a) 最靠近 DIP（位点3/7/11/15/19）
      (b) 边的方向与指尖方向(dip→tip)接近垂直（根部应⊥生长方向）
    评分 = 距离得分 + 垂直度得分，选得分最低的边
    """
    contours,_=cv2.findContours(mask_bin,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    if not contours: return None
    cnt=max(contours,key=cv2.contourArea)
    rect=cv2.minAreaRect(cnt); box=cv2.boxPoints(rect)  # (4,2)

    # 生长方向
    if tip_pt is not None:
        grow_dir=np.array([tip_pt[0]-dip_pt[0],tip_pt[1]-dip_pt[1]],dtype=np.float32)
    else:
        grow_dir=np.mean(box,axis=0)-np.array(dip_pt,dtype=np.float32)
    L=np.linalg.norm(grow_dir)
    if L<1e-6: grow_dir=np.array([0,-1],dtype=np.float32)
    else: grow_dir=grow_dir/L

    dip_arr=np.array(dip_pt,dtype=np.float32)

    # 4条边
    edges=[(box[0],box[1]),(box[1],box[2]),(box[2],box[3]),(box[3],box[0])]
    edge_mids=[np.mean(e,axis=0) for e in edges]
    edge_dirs=[np.array([e[1][0]-e[0][0],e[1][1]-e[0][1]],dtype=np.float32) for e in edges]
    edge_dirs=[d/np.linalg.norm(d) if np.linalg.norm(d)>1e-9 else np.array([1,0],dtype=np.float32) for d in edge_dirs]

    # 每条边的评分
    scores=[]
    for mid,edir in zip(edge_mids,edge_dirs):
        # 距DIP距离（归一化到0~1）
        dist=np.linalg.norm(mid-dip_arr)
        # 垂直度：|cos(edge_dir, grow_dir)| → 0=垂直(好) 1=平行(差)
        perp=np.abs(np.dot(edir,grow_dir))
        # 综合得分：距离 + 垂直度（距离主导）
        score=dist*(1.0+perp*2.0)
        scores.append(score)

    best=np.argmin(scores)

    # 根部边
    base=np.array(edges[best])
    # 指尖边 = 与根部边相对的边
    tip_edge_idx=(best+2)%4
    tip_edge=np.array(edges[tip_edge_idx])

    return {"base":base,"tip":tip_edge,"box":box,"base_mid":np.mean(base,axis=0),"base_width":np.linalg.norm(base[1]-base[0])}

def sam3_extract(img, sam3, mp_dirs=None):
    """
    SAM3 分割指甲 + MediaPipe 关键点附近区域匹配
    每个指甲根据最接近的 DIP/TIP 位点自动标注手指类型:
      拇指 = 3,4 附近  食指 = 7,8 附近  中指 = 11,12 附近
      无名指 = 15,16 附近  小指 = 19,20 附近
    """
    h,w=img.shape[:2]; sam3.set_image(img)
    masks=[]
    for prompt in ["nail","fingernail","fingernails"]:
        try:
            r=sam3(text=[prompt])
            if r and r[0].masks is not None:
                for mt in r[0].masks.data:
                    m=mt.cpu().numpy(); mbin=(m>0.5).astype(np.uint8)*255
                    mrs=cv2.resize(mbin,(w,h),interpolation=cv2.INTER_NEAREST)
                    if cv2.countNonZero(mrs)>200: masks.append(mrs)
        except: continue
    combined=np.zeros((h,w),np.uint8)
    for m in masks: combined=cv2.bitwise_or(combined,m)
    combined=cv2.morphologyEx(combined,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
    nlabels,labels,stats,centroids=cv2.connectedComponentsWithStats(combined)
    nails=[]
    for i in range(1,nlabels):
        if stats[i,4]<200: continue
        x1,y1=stats[i,0],stats[i,1]; x2=x1+stats[i,2]; y2=y1+stats[i,3]
        nm=(labels==i).astype(np.uint8)*255; nc=img[y1:y2,x1:x2].copy()
        rgba=cv2.cvtColor(nc,cv2.COLOR_BGR2BGRA); rgba[:,:,3]=nm[y1:y2,x1:x2]
        ys,xs=np.where(nm[y1:y2,x1:x2]>0)
        nails.append({"rgba":rgba,"cx":xs.mean()+x1,"cy":ys.mean()+y1,"mask":nm,"bbox":(x1,y1,x2-x1,y2-y1)})
    nails.sort(key=lambda n:n["cx"])

    # 用 MediaPipe DIP/TIP 位点附近区域标注手指类型
    if mp_dirs and len(mp_dirs)>=3:
        for n in nails:
            best_fn=None; best_dist=float('inf')
            for fn in NAMES:
                if fn not in mp_dirs: continue
                dip=mp_dirs[fn]["dip"]; tip=mp_dirs[fn]["tip"]
                # 指甲区域到 (DIP+TIP)/2 的距离
                mid=np.array([(dip[0]+tip[0])/2,(dip[1]+tip[1])/2])
                dist=np.linalg.norm(np.array([n["cx"],n["cy"]])-mid)
                if dist<best_dist:
                    best_dist=dist; best_fn=fn
            n["finger"]=best_fn
    else:
        for n in nails: n["finger"]=""

    return nails,combined

def topology_label(nails):
    if len(nails)>=3:
        lgap=nails[1]["cx"]-nails[0]["cx"]; rgap=nails[-1]["cx"]-nails[-2]["cx"]
        order=["thumb","index","middle","ring","pinky"] if lgap>rgap else ["pinky","ring","middle","index","thumb"]
        for i,n in enumerate(nails): n["finger"]=order[i] if i<len(order) else ""
        return order,lgap,rgap
    return [],0,0

def draw_nail_contours(img, nails, dirs, out_path, title=""):
    vis=img.copy()
    if title: cv2.putText(vis,title,(10,30),cv2.FONT_HERSHEY_SIMPLEX,0.7,(255,255,255),2)
    with open(out_path.replace(".png",".txt"),"w") as f:
        f.write(f"# {title}\n\n")
        for n in nails:
            fn=n.get("finger","")
            if not fn: continue
            c=COLS.get(fn,(255,255,255))
            contours,_=cv2.findContours(n["mask"],cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(vis,contours,-1,c,2)
            cx,cy=int(n["cx"]),int(n["cy"])
            cv2.circle(vis,(cx,cy),5,c,-1)
            cv2.putText(vis,fn,(cx+10,cy),cv2.FONT_HERSHEY_SIMPLEX,0.6,c,2)
            bx,by,bw,bh=n["bbox"]
            cv2.rectangle(vis,(bx,by),(bx+bw,by+bh),c,1)
            f.write(f"[{fn}] bbox=({bx},{by},{bw}x{bh}) cx=({cx},{cy})\n")
            if dirs and fn in dirs:
                dip=dirs[fn]["dip"]; tip=dirs[fn]["tip"]
                cv2.circle(vis,dip,6,(0,255,255),-1); cv2.circle(vis,tip,6,(0,0,255),-1)
                f.write(f"  DIP=({dip[0]},{dip[1]}) TIP=({tip[0]},{tip[1]}) angle={dirs[fn]['angle']}°\n")
    cv2.imwrite(out_path,vis)

def alpha_blend(result, warped, px, py, hh, hw):
    rh,rw=warped.shape[:2]
    for y in range(max(0,-py),min(rh,hh-py)):
        for x in range(max(0,-px),min(rw,hw-px)):
            a=warped[y,x,3]/255.0
            if a<0.3: continue
            ry,rx=py+y,px+x
            if 0<=ry<hh and 0<=rx<hw:
                result[ry,rx]=(warped[y,x,:3]*a+result[ry,rx]*(1-a)).astype(np.uint8)

def draw_match_lines(vis, style_nail, hand_base_mid, style_angle, hand_angle):
    """在对比图上画匹配线"""
    hh,hw=vis.shape[:2]
    # 手的根部中点
    hm=hand_base_mid
    cv2.circle(vis,(int(hm[0]),int(hm[1])),8,(0,255,0),2)


def main():
    print("="*60)
    print("  两阶段美甲试戴 v8 — a2 → a13")
    print("  阶段A: 手指属性对齐 | 阶段B: 根部线微调")
    print("="*60)
    sam3=SAM3SemanticPredictor(overrides=dict(conf=0.2,task="segment",mode="predict",model=SAM3_WT,half=False,device="cpu",save=False,verbose=False))

    # ═══════════════════════════════════════════════════════
    # Step 1+2: 先MediaPipe → 再SAM3 (用DIP/TIP位点标注手指)
    # ═══════════════════════════════════════════════════════
    print("\n[Step 1] MediaPipe a2_natural → 21位点 + DIP→TIP")
    a2_nat=cv2.imread(r"E:\meijia\style_natural\a2_natural.png")
    a2_dirs,a2_hand=mp_detect(a2_nat)
    if not a2_dirs: print("  FAILED"); return
    draw_21kp(a2_nat,a2_hand,a2_dirs,f"{OUT}/step01_a2_natural_21kp.png","a2 natural 21kp")
    for fn in NAMES: print(f"  {fn}: DIP({a2_dirs[fn]['dip']}) TIP({a2_dirs[fn]['tip']}) = {a2_dirs[fn]['angle']}°")

    print("\n[Step 2] SAM3 分割 style a2 → 5个美甲RGBA (MediaPipe位点标注)")
    a2_img=cv2.imread(r"E:\meijia\style\a2.png"); a2_h,a2_w=a2_img.shape[:2]
    a2_nails,a2_mask=sam3_extract(a2_img,sam3,a2_dirs)  # 用MediaPipe DIP/TIP标注
    cv2.imwrite(f"{OUT}/step02_a2_mask.png",a2_mask)
    for i,n in enumerate(a2_nails):
        cv2.imwrite(f"{OUT}/step02_a2_nail_{i}.png",n["rgba"])
        fn=n.get("finger","")
        if fn: print(f"  nail_{i} → {fn}")
    print(f"  {len(a2_nails)} nails extracted")

    # ═══════════════════════════════════════════════════════
    # Step 3: SAM3轮廓标注 + 指尖方向
    # ═══════════════════════════════════════════════════════
    print("\n[Step 3] SAM3轮廓 + MediaPipe指尖方向 (style a2)")
    print(f"  手指配对 (MediaPipe DIP/TIP位点): {[(n.get('finger','?')) for n in a2_nails]}")
    draw_nail_contours(a2_img,a2_nails,a2_dirs,f"{OUT}/step03_a2_contours.png","Style a2 - SAM3 + MediaPipe Finger Labels")

    # ═══════════════════════════════════════════════════════
    # Step 3b: MediaPipe + SAM3 分割 hand → 轮廓+手指标签
    # ═══════════════════════════════════════════════════════
    print("\n[Step 3b] MediaPipe + SAM3 分割 hand → 轮廓+手指标签")
    a13_img=cv2.imread(r"E:\meijia\hands\a13.png"); a13_h,a13_w=a13_img.shape[:2]
    a13_dirs,a13_hand=mp_detect(a13_img)
    a13_nails,a13_mask=sam3_extract(a13_img,sam3,a13_dirs)  # 用MediaPipe DIP/TIP标注
    print(f"  Hand 手指配对 (MediaPipe位点): {[(n.get('finger','?')) for n in a13_nails]}")
    for n in a13_nails:
        fn=n.get("finger","")
        if fn and fn in a13_dirs: print(f"    {fn}: cx={n['cx']:.0f} angle={a13_dirs[fn]['angle']}°")
    draw_nail_contours(a13_img,a13_nails,a13_dirs,f"{OUT}/step03b_a13_contours.png","Hand - SAM3 + MediaPipe Finger Labels")

    # ═══════════════════════════════════════════════════════
    # Step 4: MediaPipe hand → 21位点可视化
    # ═══════════════════════════════════════════════════════
    print("\n[Step 4] MediaPipe hand → 21位点 + DIP→TIP 可视化")
    draw_21kp(a13_img,a13_hand,a13_dirs,f"{OUT}/step04_a13_hand_21kp.png","hand 21kp")

    # ═══════════════════════════════════════════════════════
    # Step 5: [阶段A] 手指属性对齐
    # 指甲已在 Step 2/3b 中由 MediaPipe DIP/TIP 位点自动标注
    # 直接按 finger 名字配对: thumb↔thumb, index↔index, ...
    # ═══════════════════════════════════════════════════════
    print("\n" + "─"*60)
    print("[Step 5] 阶段A — 手指属性对齐 (MediaPipe位点直接配对)")
    print("  方法: 每个指甲由最近的MediaPipe DIP/TIP位点标注")
    print("        thumb↔thumb index↔index middle↔middle ring↔ring pinky↔pinky")
    print("─"*60)

    # 使用手部natural图作为基底 (生成式补齐: 天然裸甲填充未覆盖区域)
    hand_natural_path=rf"E:\meijia\hands_natural\{'a13' if 'a13' in 'hand_a13' else 'a14'}.png"
    # 自动匹配实际文件名
    import glob
    natural_candidates=list(Path(r"E:\meijia\hands_natural").glob("*.png"))+list(Path(r"E:\meijia\style_natural").glob("*.png"))
    # 简单起见，用现有natural图
    if os.path.exists(rf"E:\meijia\hands_natural\a13_natural.png"):
        base_img=cv2.imread(rf"E:\meijia\hands_natural\a13_natural.png")
        if base_img.shape[:2]==(a13_h,a13_w):
            stageA_result=base_img.copy()
        else:
            stageA_result=a13_img.copy()
    else:
        stageA_result=a13_img.copy()

    stageA_log=[]
    stageA_log.append("# 阶段A: 手指属性对齐 (MediaPipe位点直接配对 + natural基底)\n\n")

    for sn in a2_nails:
        fn=sn.get("finger","")
        if not fn or fn not in a2_dirs or fn not in a13_dirs: continue

        rgba=sn["rgba"]; nh,nw=rgba.shape[:2]
        s_angle=a2_dirs[fn]["angle"]; h_angle=a13_dirs[fn]["angle"]
        rot=h_angle-s_angle

        M=cv2.getRotationMatrix2D((nw/2,nh/2),rot,1.0)
        cos,sin=abs(M[0,0]),abs(M[0,1])
        rw,rh=int(nh*sin+nw*cos),int(nh*cos+nw*sin)
        M[0,2]+=rw/2-nw/2; M[1,2]+=rh/2-nh/2
        warped=cv2.warpAffine(rgba,M,(rw,rh),flags=cv2.INTER_LANCZOS4,borderMode=cv2.BORDER_CONSTANT,borderValue=(0,0,0,0))

        # 质心定位到hand TIP
        wcx,wcy=np.dot(M[:,:2],[nw/2,nh/2])+M[:,2]
        h_tip=a13_dirs[fn]["tip"]
        px,py=int(h_tip[0]-wcx),int(h_tip[1]-wcy)

        alpha_blend(stageA_result,warped,px,py,a13_h,a13_w)

        stageA_log.append(f"[{fn}] s_angle={s_angle}° h_angle={h_angle}° rot={rot:.0f}° → hand TIP=({h_tip[0]},{h_tip[1]})\n")
        print(f"  {fn}→{fn}: rot={rot:.0f}° TIP定位完成")

    cv2.imwrite(f"{OUT}/step05_stageA_rough.png",stageA_result)
    with open(f"{OUT}/step05_stageA_log.txt","w") as f:
        for l in stageA_log: f.write(l)
    print(f"  → step05_stageA_rough.png (natural基底+美甲覆盖)")

    # ═══════════════════════════════════════════════════════
    # Step 6: minAreaRect 找根部边
    # ═══════════════════════════════════════════════════════
    print("\n" + "─"*60)
    print("[Step 6] minAreaRect 找根部边 — 准备阶段B微调")
    print("─"*60)

    step6_lines=[]
    vis_a2=a2_img.copy()
    for n in a2_nails:
        fn=n.get("finger","")
        if not fn or fn not in a2_dirs: continue
        edge=get_base_edge(n["mask"],a2_dirs[fn]["dip"],a2_dirs[fn]["tip"])
        if edge is None: continue
        n["base"]=edge
        c=COLS[fn]
        cv2.drawContours(vis_a2,[np.int32(edge["box"])],-1,c,2)
        b1=tuple(edge["base"][0].astype(int)); b2=tuple(edge["base"][1].astype(int))
        cv2.line(vis_a2,b1,b2,(0,255,255),3)
        step6_lines.append(f"style_{fn}: base_mid=({edge['base_mid'][0]:.0f},{edge['base_mid'][1]:.0f}) base_w={edge['base_width']:.0f}px")
        print(f"  style_{fn}: base_mid=({edge['base_mid'][0]:.0f},{edge['base_mid'][1]:.0f}) w={edge['base_width']:.0f}px")
    cv2.imwrite(f"{OUT}/step06_a2_root_edges.png",vis_a2)

    vis_a13=a13_img.copy()
    for n in a13_nails:
        fn=n.get("finger","")
        if not fn or fn not in a13_dirs: continue
        edge=get_base_edge(n["mask"],a13_dirs[fn]["dip"],a13_dirs[fn]["tip"])
        if edge is None: continue
        n["base"]=edge
        c=COLS[fn]
        cv2.drawContours(vis_a13,[np.int32(edge["box"])],-1,c,2)
        b1=tuple(edge["base"][0].astype(int)); b2=tuple(edge["base"][1].astype(int))
        cv2.line(vis_a13,b1,b2,(0,255,255),3)
        step6_lines.append(f"hand_{fn}: base_mid=({edge['base_mid'][0]:.0f},{edge['base_mid'][1]:.0f}) base_w={edge['base_width']:.0f}px")
        print(f"  hand_{fn}: base_mid=({edge['base_mid'][0]:.0f},{edge['base_mid'][1]:.0f}) w={edge['base_width']:.0f}px")
    cv2.imwrite(f"{OUT}/step06_a13_root_edges.png",vis_a13)

    with open(f"{OUT}/step06_roots.txt","w") as f:
        f.write("# 根部边数据 (阶段B输入)\n\n")
        for l in step6_lines: f.write(l+"\n")

    # ═══════════════════════════════════════════════════════
    # Step 7: [阶段B] 等比缩放填满目标指甲轮廓
    # 基于阶段A方向对齐结果，等比例缩放使美甲完全覆盖目标指甲区域
    # ═══════════════════════════════════════════════════════
    print("\n" + "─"*60)
    print("[Step 7] 阶段B — 等比缩放填满目标指甲轮廓")
    print("  方法: 计算target指甲面积 → 缩放style美甲使其完全覆盖")
    print("        美甲严格位于目标指甲位置 + mask裁剪超出的部分")
    print("─"*60)

    stageB_result=stageA_result.copy()  # 基于阶段A的natural基底
    stageB_log=[]
    stageB_log.append("# 阶段B: 等比缩放填满目标指甲轮廓\n")
    stageB_log.append("# scale = sqrt(target_area / style_area) * cover_factor\n\n")

    # 为每个目标手指生成 nail mask（裁剪到mask内）
    total_target_mask=np.zeros((a13_h,a13_w),dtype=np.uint8)

    for sn in a2_nails:
        fn=sn.get("finger","")
        if not fn or fn not in a2_dirs or fn not in a13_dirs: continue

        # 找同属性hand指甲
        hn=None
        for tn in a13_nails:
            if tn.get("finger")==fn: hn=tn; break
        if hn is None: continue

        rgba=sn["rgba"]; nh,nw=rgba.shape[:2]
        s_angle=a2_dirs[fn]["angle"]; h_angle=a13_dirs[fn]["angle"]
        rot=h_angle-s_angle

        # 计算目标面积和缩放
        target_area=np.sum(hn["mask"]>0)
        style_area=np.sum(sn["mask"]>0)
        # 等比缩放系数: 使美甲面积 = 目标面积 * 1.3 (覆盖因子)
        area_scale=np.sqrt(target_area/max(style_area,1))*1.3
        scale=max(area_scale,0.5)

        M=cv2.getRotationMatrix2D((nw/2,nh/2),rot,scale)
        cos,sin=abs(M[0,0]),abs(M[0,1])
        rw,rh=int(nh*sin+nw*cos),int(nh*cos+nw*sin)
        M[0,2]+=rw/2-nw/2; M[1,2]+=rh/2-nh/2
        warped=cv2.warpAffine(rgba,M,(rw,rh),flags=cv2.INTER_LANCZOS4,borderMode=cv2.BORDER_CONSTANT,borderValue=(0,0,0,0))

        # 定位到hand TIP
        wcx,wcy=np.dot(M[:,:2],[nw/2,nh/2])+M[:,2]
        h_tip=a13_dirs[fn]["tip"]
        px,py=int(h_tip[0]-wcx),int(h_tip[1]-wcy)

        # 对目标手部mask做dilation得到裁剪区域
        target_mask_roi=cv2.dilate(hn["mask"],np.ones((15,15),np.uint8))

        # Alpha融合 (美甲严格在目标指甲区域)
        for y in range(max(0,-py),min(rh,a13_h-py)):
            for x in range(max(0,-px),min(rw,a13_w-px)):
                ry,rx=py+y,px+x
                if not (0<=ry<a13_h and 0<=rx<a13_w): continue
                a=warped[y,x,3]/255.0
                if a<0.3: continue
                # 限制在目标指甲轮廓内 (dilation后的区域)
                if target_mask_roi[ry,rx]==0: continue
                stageB_result[ry,rx]=(warped[y,x,:3]*a+stageB_result[ry,rx]*(1-a)).astype(np.uint8)

        stageB_log.append(f"[{fn}] rot={rot:.0f}° scale={scale:.2f}(area) area {style_area}→{target_area}px TIP定位\n")
        print(f"  {fn}: rot={rot:.0f}° scale={scale:.2f} area覆盖 target面积{target_area}px")

    cv2.imwrite(f"{OUT}/step07_stageB_final.png",stageB_result)
    with open(f"{OUT}/step07_stageB_log.txt","w") as f:
        for l in stageB_log: f.write(l)

    # ═══════════════════════════════════════════════════════
    # Summary
    # ═══════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"全部完成 → {OUT}")
    print(f"\n阶段A (手指属性对齐): step05_stageA_rough.png")
    print(f"阶段B (根部线微调):   step07_stageB_final.png")
    print(f"\n文件清单:")
    for f in sorted(os.listdir(OUT)):
        sz=os.path.getsize(os.path.join(OUT,f))
        tag=""
        if "stageA" in f: tag=" [阶段A]"
        elif "stageB" in f: tag=" [阶段B]"
        elif "root" in f: tag=" [根部]"
        print(f"  {f}{tag}")

if __name__=="__main__":
    main()
