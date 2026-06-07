"""
nail_wear_v7.py — 完整美甲试戴 (含轮廓标注步骤)
=============================================
步骤:
  Step1: SAM3 分割 style a2 → 5个RGBA美甲单独保存
  Step2: MediaPipe 检测 a2_natural → 21位点 + DIP→TIP方向
  Step3: 拓扑法标注手指类型 → SAM3轮廓+手指标签图
  Step3b: SAM3 分割 hand a13 → 轮廓+手指标签图
  Step4: minAreaRect 找根部边 (style + hand)
  Step5: 旋转对齐 + 根部重合 + 佩戴

用法: python E:\meijia\nail_wear_v7.py
"""

import cv2, numpy as np, json, math, os
from pathlib import Path
from ultralytics.models.sam import SAM3SemanticPredictor
import mediapipe as mp
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision

SAM3_WT = r"E:\meijia\sam3_wights\sam3.pt"
LM = r"E:\meijia\hand_landmarker.task"
OUT = r"E:\meijia\z_wear_v7"
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

def draw_21kp(img,hand,dirs,out_path):
    h,w=img.shape[:2]; vis=img.copy()
    for a,b in CONNS: cv2.line(vis,(int(hand[a].x*w),int(hand[a].y*h)),(int(hand[b].x*w),int(hand[b].y*h)),(180,180,180),1)
    for i in range(21): pt=(int(hand[i].x*w),int(hand[i].y*h)); cv2.circle(vis,pt,3,(200,200,200),-1); cv2.putText(vis,str(i),(pt[0]+3,pt[1]-3),cv2.FONT_HERSHEY_SIMPLEX,0.3,(180,180,180),1)
    for fn in NAMES:
        d=dirs[fn]; c=COLS[fn]; L=math.sqrt((d['tip'][0]-d['dip'][0])**2+(d['tip'][1]-d['dip'][1])**2) or 1
        ext=(int(d['tip'][0]+(d['tip'][0]-d['dip'][0])/L*60),int(d['tip'][1]+(d['tip'][1]-d['dip'][1])/L*60))
        cv2.arrowedLine(vis,d['dip'],ext,c,2,tipLength=0.3); cv2.circle(vis,d['dip'],5,(0,255,255),-1); cv2.circle(vis,d['tip'],6,(0,0,255),-1)
        cv2.putText(vis,f"{fn} {d['angle']}°",(d['tip'][0]+8,d['tip'][1]),cv2.FONT_HERSHEY_SIMPLEX,0.45,c,1)
    cv2.imwrite(out_path,vis)

def get_base_edge(mask_bin, dip_pt):
    contours,_=cv2.findContours(mask_bin,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    if not contours: return None
    cnt=max(contours,key=cv2.contourArea)
    rect=cv2.minAreaRect(cnt); box=cv2.boxPoints(rect)
    dip_arr=np.array(dip_pt,dtype=np.float32)
    dists=np.linalg.norm(box-dip_arr,axis=1); order=np.argsort(dists)
    base_idx=sorted(order[:2]); tip_idx=sorted(order[2:])
    base=box[base_idx]; tip=box[tip_idx]
    return {"base":base, "tip":tip, "box":box, "base_mid":np.mean(base,axis=0), "base_width":np.linalg.norm(base[1]-base[0])}

def sam3_extract(img, sam3):
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
        nm=(labels==i).astype(np.uint8)*255
        nc=img[y1:y2,x1:x2].copy()
        rgba=cv2.cvtColor(nc,cv2.COLOR_BGR2BGRA); rgba[:,:,3]=nm[y1:y2,x1:x2]
        ys,xs=np.where(nm[y1:y2,x1:x2]>0)
        nails.append({"rgba":rgba,"cx":xs.mean()+x1,"cy":ys.mean()+y1,"mask":nm,"bbox":(x1,y1,x2-x1,y2-y1)})
    nails.sort(key=lambda n:n["cx"])
    return nails,combined

def topology_label(nails):
    if len(nails)>=3:
        lgap=nails[1]["cx"]-nails[0]["cx"]; rgap=nails[-1]["cx"]-nails[-2]["cx"]
        order=["thumb","index","middle","ring","pinky"] if lgap>rgap else ["pinky","ring","middle","index","thumb"]
        for i,n in enumerate(nails): n["finger"]=order[i] if i<len(order) else ""
        return order,lgap,rgap
    return [],0,0

def draw_nail_contours(img, nails, dirs, out_path, title=""):
    """画出SAM3指甲轮廓 + 手指标签"""
    vis=img.copy()
    cv2.putText(vis,title,(10,30),cv2.FONT_HERSHEY_SIMPLEX,0.8,(255,255,255),2)
    
    with open(out_path.replace(".png",".txt"),"w") as f:
        f.write(f"# {title}\n\n")
        for n in nails:
            fn=n.get("finger","")
            if not fn: continue
            c=COLS.get(fn,(255,255,255))
            # 画轮廓
            contours,_=cv2.findContours(n["mask"],cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(vis,contours,-1,c,2)
            # 画质心+标签
            cx,cy=int(n["cx"]),int(n["cy"])
            cv2.circle(vis,(cx,cy),5,c,-1)
            cv2.putText(vis,fn,(cx+10,cy),cv2.FONT_HERSHEY_SIMPLEX,0.6,c,2)
            # 写bbox
            bx,by,bw,bh=n["bbox"]
            cv2.rectangle(vis,(bx,by),(bx+bw,by+bh),c,1)
            
            f.write(f"[{fn}] bbox=({bx},{by},{bw}x{bh}) cx=({cx},{cy})\n")
            if dirs and fn in dirs:
                dip=dirs[fn]["dip"]; tip=dirs[fn]["tip"]
                cv2.circle(vis,dip,6,(0,255,255),-1)
                cv2.circle(vis,tip,6,(0,0,255),-1)
                f.write(f"  DIP=({dip[0]},{dip[1]}) TIP=({tip[0]},{tip[1]}) angle={dirs[fn]['angle']}°\n")
    
    cv2.imwrite(out_path,vis)
    return


def main():
    print("="*56)
    print("  完整美甲试戴 v7 — a2 → a13")
    print("="*56)
    sam3=SAM3SemanticPredictor(overrides=dict(conf=0.2,task="segment",mode="predict",model=SAM3_WT,half=False,device="cpu",save=False,verbose=False))

    # ═══ STEP 1: SAM3 分割 a2 + 单独保存美甲 ═══
    print("\n[Step 1] SAM3 分割 style a2 → 5个美甲RGBA")
    a2_img=cv2.imread(r"E:\meijia\style\a2.png"); a2_h,a2_w=a2_img.shape[:2]
    a2_nails,a2_mask=sam3_extract(a2_img,sam3)
    cv2.imwrite(f"{OUT}/step1_a2_mask.png",a2_mask)
    for i,n in enumerate(a2_nails):
        cv2.imwrite(f"{OUT}/step1_a2_nail_{i}.png",n["rgba"])
        print(f"  step1_a2_nail_{i}.png saved")

    # ═══ STEP 2: MediaPipe a2_natural → 21位点+方向 ═══
    print("\n[Step 2] MediaPipe a2_natural → 21位点+DIP→TIP")
    a2_nat=cv2.imread(r"E:\meijia\style_natural\a2_natural.png")
    a2_dirs,a2_hand=mp_detect(a2_nat)
    if a2_dirs:
        draw_21kp(a2_nat,a2_hand,a2_dirs,f"{OUT}/step2_a2_21kp.png")
        for fn in NAMES: print(f"  {fn}: {a2_dirs[fn]['angle']}°")
    else:
        print("  FAILED"); return

    # ═══ STEP 3: 拓扑法 + SAM3轮廓标注 (style a2) ═══
    print("\n[Step 3] 拓扑法标注 + SAM3轮廓 (style a2)")
    order,lgap,rgap=topology_label(a2_nails)
    print(f"  拓扑: left_gap={lgap:.0f} right_gap={rgap:.0f} → {order}")
    draw_nail_contours(a2_img,a2_nails,a2_dirs,
                       f"{OUT}/step3_a2_contours.png",
                       f"Style a2 - SAM3 Nail Contours ({len(a2_nails)} nails)")
    print(f"  step3_a2_contours.png saved")
    print(f"  step3_a2_contours.txt saved")

    # ═══ STEP 3b: SAM3 分割 hand a13 + 轮廓标注 ═══
    print("\n[Step 3b] SAM3 分割 hand a13 → 轮廓+手指标签")
    a13_img=cv2.imread(r"E:\meijia\hands\a13.png"); a13_h,a13_w=a13_img.shape[:2]
    a13_dirs,a13_hand=mp_detect(a13_img)
    
    a13_nails,a13_mask=sam3_extract(a13_img,sam3)
    
    # 标注手指类型
    if a13_dirs and len(a13_dirs)>=5:
        mp_xs=[a13_dirs[fn]["dip"][0] for fn in NAMES]
        thumb_left=mp_xs[0]<mp_xs[4]
        for n in a13_nails: n["finger"]=""
        for i in range(min(len(a13_nails),5)):
            idx=i if thumb_left else len(a13_nails)-1-i
            a13_nails[idx]["finger"]=NAMES[i]
    else:
        topology_label(a13_nails)
    
    draw_21kp(a13_img,a13_hand,a13_dirs,f"{OUT}/step3b_a13_21kp.png")
    draw_nail_contours(a13_img,a13_nails,a13_dirs,
                       f"{OUT}/step3b_a13_contours.png",
                       f"Hand a13 - SAM3 Nail Contours ({len(a13_nails)} nails)")
    print(f"  step3b_a13_contours.png + .txt saved")
    for n in a13_nails:
        fn=n.get("finger","")
        if fn: print(f"  {fn}: cx={n['cx']:.0f}")

    # ═══ STEP 4: minAreaRect 找根部边 ═══
    print("\n[Step 4] minAreaRect 找根部边")
    
    step4_lines=[]
    # Style a2
    vis_a2=a2_img.copy()
    for n in a2_nails:
        fn=n.get("finger","")
        if not fn or fn not in a2_dirs: continue
        dip=a2_dirs[fn]["dip"]
        edge=get_base_edge(n["mask"],dip)
        if edge is None: continue
        n["base"]=edge
        c=COLS[fn]
        cv2.drawContours(vis_a2,[np.int32(edge["box"])],-1,c,2)
        b1=tuple(edge["base"][0].astype(int)); b2=tuple(edge["base"][1].astype(int))
        cv2.line(vis_a2,b1,b2,(0,255,255),3)
        cv2.circle(vis_a2,dip,6,c,-1)
        cv2.putText(vis_a2,fn,(int(dip[0])+10,int(dip[1])-10),cv2.FONT_HERSHEY_SIMPLEX,0.5,c,1)
        step4_lines.append(f"style_{fn}: base_w={edge['base_width']:.0f} base_mid=({edge['base_mid'][0]:.0f},{edge['base_mid'][1]:.0f})")
        print(f"  style_{fn}: base_w={edge['base_width']:.0f}px")
    cv2.imwrite(f"{OUT}/step4_a2_roots.png",vis_a2)

    # Hand a13
    vis_a13=a13_img.copy()
    for n in a13_nails:
        fn=n.get("finger","")
        if not fn or fn not in a13_dirs: continue
        dip=a13_dirs[fn]["dip"]
        edge=get_base_edge(n["mask"],dip)
        if edge is None: continue
        n["base"]=edge
        c=COLS[fn]
        cv2.drawContours(vis_a13,[np.int32(edge["box"])],-1,c,2)
        b1=tuple(edge["base"][0].astype(int)); b2=tuple(edge["base"][1].astype(int))
        cv2.line(vis_a13,b1,b2,(0,255,255),3)
        cv2.circle(vis_a13,dip,6,c,-1)
        step4_lines.append(f"hand_{fn}: base_w={edge['base_width']:.0f} base_mid=({edge['base_mid'][0]:.0f},{edge['base_mid'][1]:.0f})")
        print(f"  hand_{fn}: base_w={edge['base_width']:.0f}px")
    cv2.imwrite(f"{OUT}/step4_a13_roots.png",vis_a13)

    with open(f"{OUT}/step4_roots.txt","w") as f:
        f.write("# minAreaRect 根部边\n\n")
        for line in step4_lines: f.write(line+"\n")

    # ═══ STEP 5: 根部重合 + 佩戴 ═══
    print("\n[Step 5] 根部重合 + 旋转对齐 + 佩戴")
    result=a13_img.copy()
    
    step5_lines=["# a2 → a13 根部对齐佩戴\n\n"]
    for n in a2_nails:
        fn=n.get("finger","")
        if not fn or fn not in a2_dirs or fn not in a13_dirs: continue
        if "base" not in n: continue
        
        tgt=None
        for tn in a13_nails:
            if tn.get("finger")==fn and "base" in tn: tgt=tn; break
        if tgt is None: continue
        
        rgba=n["rgba"]; nh,nw=rgba.shape[:2]
        s_angle=a2_dirs[fn]["angle"]; h_angle=a13_dirs[fn]["angle"]
        rot=h_angle-s_angle
        
        s_base_w=n["base"]["base_width"]; h_base_w=tgt["base"]["base_width"]
        scale=h_base_w/max(s_base_w,1)*1.1
        
        M=cv2.getRotationMatrix2D((nw/2,nh/2),rot,scale)
        cos,sin=abs(M[0,0]),abs(M[0,1])
        rw,rh=int(nh*sin+nw*cos),int(nh*cos+nw*sin)
        M[0,2]+=rw/2-nw/2; M[1,2]+=rh/2-nh/2
        warped=cv2.warpAffine(rgba,M,(rw,rh),flags=cv2.INTER_LANCZOS4,
                              borderMode=cv2.BORDER_CONSTANT,borderValue=(0,0,0,0))
        
        s_base_mid=n["base"]["base_mid"]
        warped_base=np.dot(M[:,:2],s_base_mid)+M[:,2]
        h_base_mid=tgt["base"]["base_mid"]
        px,py=int(h_base_mid[0]-warped_base[0]),int(h_base_mid[1]-warped_base[1])
        
        for y in range(max(0,-py),min(rh,a13_h-py)):
            for x in range(max(0,-px),min(rw,a13_w-px)):
                a=warped[y,x,3]/255.0
                if a<0.3: continue
                ry,rx=py+y,px+x
                if 0<=ry<a13_h and 0<=rx<a13_w:
                    result[ry,rx]=(warped[y,x,:3]*a+result[ry,rx]*(1-a)).astype(np.uint8)
        
        step5_lines.append(f"[{fn}] rot={rot:.0f}° scale={scale:.3f} base_w {s_base_w:.0f}→{h_base_w:.0f}px ✓\n")
        print(f"  {fn}: rot={rot:.0f}° scale={scale:.2f} base对齐 ✓")

    cv2.imwrite(f"{OUT}/step5_result.png",result)
    with open(f"{OUT}/step5_wear_log.txt","w") as f:
        for line in step5_lines: f.write(line)

    print(f"\n{'='*56}")
    print(f"全部完成 → {OUT}")
    for f in sorted(os.listdir(OUT)):
        sz=os.path.getsize(os.path.join(OUT,f))
        print(f"  {f} ({sz/1024:.0f}KB)" if sz>1024 else f"  {f}")

if __name__=="__main__":
    main()
