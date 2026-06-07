"""
run.py — 美甲试戴一键运行 (传统方法完整流程)
==========================================
用法: python run.py style=a8 hand=a13

流程:
  Step1: SAM3 分割 + MediaPipe 标注 → E:\meijia\model\output\s1
  Step2: SD Inpainting 擦除美甲 → E:\meijia\model\output\s2
  Step3: 两阶段试戴 → E:\meijia\model\output\result

所有模型、代码均在 E:\meijia\model\ 下，不依赖外部 .py 文件。
"""

import os, sys, cv2, numpy as np, math, argparse
from pathlib import Path
from ultralytics.models.sam import SAM3SemanticPredictor
import mediapipe as mp
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision

# ── 路径 (全部在本目录下) ─────────────────────────────────
BASE    = os.path.dirname(os.path.abspath(__file__))
SAM3_WT = os.path.join(BASE, "sam3.pt")
LM_PATH = os.path.join(BASE, "hand_landmarker.task")
OUT     = os.path.join(BASE, "output")

F_DIP   = [3, 7, 11, 15, 19]
F_TIP   = [4, 8, 12, 16, 20]
FINGERS = ["thumb", "index", "middle", "ring", "pinky"]
COLS_BGR = {"thumb":(0,255,0),"index":(255,0,0),"middle":(0,0,255),"ring":(255,0,255),"pinky":(0,255,255)}
CONNS = [(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),(0,9),(9,10),(10,11),(11,12),(0,13),(13,14),(14,15),(15,16),(0,17),(17,18),(18,19),(19,20),(5,9),(9,13),(13,17)]


def lk_angle(x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L = math.sqrt(dx * dx + dy * dy)
    if L == 0: return 0.0
    deg = math.degrees(math.asin(abs(dy) / L))
    if dx > 0 and dy < 0:     return deg
    elif dx < 0 and dy < 0:   return 180 - deg
    elif dx < 0 and dy > 0:   return 180 + deg
    else:                     return 360 - deg


def mp_detect(img_bgr):
    h, w = img_bgr.shape[:2]
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB,
                      data=cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    for conf in [0.3, 0.2, 0.1, 0.05]:
        opt = vision.HandLandmarkerOptions(
            base_options=mpt.BaseOptions(model_asset_path=LM_PATH),
            num_hands=2, min_hand_detection_confidence=conf)
        det = vision.HandLandmarker.create_from_options(opt)
        res = det.detect(mp_img); det.close()
        if res and res.hand_landmarks:
            hand = res.hand_landmarks[0]; dirs = {}
            for fn, di, ti in zip(FINGERS, F_DIP, F_TIP):
                tx = int(hand[ti].x * w); ty = int(hand[ti].y * h)
                dx = int(hand[di].x * w); dy = int(hand[di].y * h)
                dirs[fn] = {"tip": (tx, ty), "dip": (dx, dy),
                            "angle": round(lk_angle(dx, dy, tx, ty), 1)}
            return dirs
    return {}


def sam3_extract(img_bgr, sam3_model, mp_dirs=None):
    h, w = img_bgr.shape[:2]
    sam3_model.set_image(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    masks = []
    for prompt in ["nail", "fingernail", "fingernails"]:
        try:
            r = sam3_model(text=[prompt])
            if r and r[0].masks is not None:
                for mt in r[0].masks.data:
                    m = mt.cpu().numpy()
                    mbin = (m > 0.5).astype(np.uint8) * 255
                    mrs = cv2.resize(mbin, (w, h), interpolation=cv2.INTER_NEAREST)
                    if cv2.countNonZero(mrs) > 200: masks.append(mrs)
        except: continue
    if not masks: return [], np.zeros((h, w), np.uint8)
    combined = np.zeros((h, w), np.uint8)
    for m in masks: combined = cv2.bitwise_or(combined, m)
    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    nlabels, labels, stats, centroids = cv2.connectedComponentsWithStats(combined)
    nails = []
    for i in range(1, nlabels):
        if stats[i, 4] < 200: continue
        x1, y1 = stats[i, 0], stats[i, 1]; x2, y2 = x1 + stats[i, 2], y1 + stats[i, 3]
        nm = (labels == i).astype(np.uint8) * 255
        nc = img_bgr[y1:y2, x1:x2].copy()
        rgba = cv2.cvtColor(nc, cv2.COLOR_BGR2BGRA); rgba[:, :, 3] = nm[y1:y2, x1:x2]
        ys, xs = np.where(nm[y1:y2, x1:x2] > 0)
        nails.append({"rgba": rgba, "cx": xs.mean() + x1, "cy": ys.mean() + y1,
                       "mask": nm, "bbox": (x1, y1, x2 - x1, y2 - y1)})
    if mp_dirs and len(mp_dirs) >= 3:
        for n in nails:
            best_fn, best_dist = None, float('inf')
            for fn in FINGERS:
                if fn not in mp_dirs: continue
                dip = mp_dirs[fn]["dip"]; tip = mp_dirs[fn]["tip"]
                mid = np.array([(dip[0] + tip[0]) / 2, (dip[1] + tip[1]) / 2])
                dist = np.linalg.norm(np.array([n["cx"], n["cy"]]) - mid)
                if dist < best_dist: best_dist, best_fn = dist, fn
            n["finger"] = best_fn
    else:
        for n in nails: n["finger"] = ""
    return nails, combined


def draw_21kp(img, hand_lm, dirs, out_path):
    h, w = img.shape[:2]; vis = img.copy()
    for a, b in CONNS:
        cv2.line(vis, (int(hand_lm[a].x * w), int(hand_lm[a].y * h)),
                 (int(hand_lm[b].x * w), int(hand_lm[b].y * h)), (180, 180, 180), 1)
    for i in range(21):
        pt = (int(hand_lm[i].x * w), int(hand_lm[i].y * h))
        cv2.circle(vis, pt, 3, (200, 200, 200), -1)
    for fn in FINGERS:
        d = dirs[fn]; c = COLS_BGR[fn]
        L = math.sqrt((d['tip'][0] - d['dip'][0]) ** 2 + (d['tip'][1] - d['dip'][1]) ** 2) or 1
        ext = (int(d['tip'][0] + (d['tip'][0] - d['dip'][0]) / L * 60),
               int(d['tip'][1] + (d['tip'][1] - d['dip'][1]) / L * 60))
        cv2.arrowedLine(vis, d['dip'], ext, c, 2, tipLength=0.3)
        cv2.circle(vis, d['dip'], 5, (0, 255, 255), -1)
        cv2.circle(vis, d['tip'], 6, (0, 0, 255), -1)
        cv2.putText(vis, f"{fn} {d['angle']}°", (d['tip'][0] + 8, d['tip'][1]),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, c, 1)
    cv2.imwrite(out_path, vis)


def draw_contours(img, nails, dirs, out_path, title=""):
    vis = img.copy()
    if title: cv2.putText(vis, title, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    for n in nails:
        fn = n.get("finger", "")
        if not fn: continue
        c = COLS_BGR.get(fn, (255, 255, 255))
        cnts, _ = cv2.findContours(n["mask"], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(vis, cnts, -1, c, 2)
        cx, cy = int(n["cx"]), int(n["cy"])
        cv2.circle(vis, (cx, cy), 5, c, -1)
        cv2.putText(vis, fn, (cx + 10, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.6, c, 2)
    cv2.imwrite(out_path, vis)


def wear(style_nails, hand_dirs, style_dirs, hand_img, hand_nails, out_path):
    hh, hw = hand_img.shape[:2]
    result = hand_img.copy()
    for sn in style_nails:
        fn = sn.get("finger", "")
        if not fn or fn not in style_dirs or fn not in hand_dirs: continue
        hn = None
        for tn in hand_nails:
            if tn.get("finger") == fn: hn = tn; break
        if hn is None: continue
        rgba = sn["rgba"]; nh, nw = rgba.shape[:2]
        rot = hand_dirs[fn]["angle"] - style_dirs[fn]["angle"]
        target_area = max(np.sum(hn["mask"] > 0), 1)
        style_area = max(np.sum(sn["mask"] > 0), 1)
        scale = max(math.sqrt(target_area / style_area) * 1.3, 0.5)
        M = cv2.getRotationMatrix2D((nw / 2, nh / 2), rot, scale)
        cos, sin = abs(M[0, 0]), abs(M[0, 1])
        rw, rh = int(nh * sin + nw * cos), int(nh * cos + nw * sin)
        M[0, 2] += rw / 2 - nw / 2; M[1, 2] += rh / 2 - nh / 2
        warped = cv2.warpAffine(rgba, M, (rw, rh), flags=cv2.INTER_LANCZOS4,
                                borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        wcx, wcy = np.dot(M[:, :2], [nw / 2, nh / 2]) + M[:, 2]
        h_dip = hand_dirs[fn]["dip"]
        px, py = int(h_dip[0] - wcx), int(h_dip[1] - wcy)
        target_roi = cv2.dilate(hn["mask"], np.ones((15, 15), np.uint8))
        for y in range(max(0, -py), min(rh, hh - py)):
            for x in range(max(0, -px), min(rw, hw - px)):
                ry, rx = py + y, px + x
                if not (0 <= ry < hh and 0 <= rx < hw): continue
                a = warped[y, x, 3] / 255.0
                if a < 0.3: continue
                if target_roi[ry, rx] == 0: continue
                result[ry, rx] = (warped[y, x, :3] * a + result[ry, rx] * (1 - a)).astype(np.uint8)
    cv2.imwrite(out_path, result)
    return result


def main():
    parser = argparse.ArgumentParser(description="美甲试戴一键运行")
    parser.add_argument("--style", required=True, help="款式图文件名, e.g. a8")
    parser.add_argument("--hand", required=True, help="手部图文件名, e.g. a13")
    parser.add_argument("--style_dir", default=r"E:\meijia\style")
    parser.add_argument("--hand_dir", default=r"E:\meijia\hands")
    parser.add_argument("--natural_dir", default=r"E:\meijia\style_natural")
    args = parser.parse_args()

    style_stem = args.style.replace(".png", "")
    hand_stem  = args.hand.replace(".png", "")
    os.makedirs(OUT, exist_ok=True)

    style_path = os.path.join(args.style_dir, f"{style_stem}.png")
    hand_path  = os.path.join(args.hand_dir, f"{hand_stem}.png")
    style_nat  = os.path.join(args.natural_dir, f"{style_stem}_natural.png")

    print("=" * 56)
    print(f"  美甲试戴 {style_stem} → {hand_stem}")
    print("=" * 56)

    sam3 = SAM3SemanticPredictor(overrides=dict(
        conf=0.2, task="segment", mode="predict", model=SAM3_WT,
        half=False, device="cpu", save=False, verbose=False))

    # ── Step 1: Style 图 SAM3 + MediaPipe (优先natural) ──
    print("\n[Step 1] Style 图: SAM3分割 + MediaPipe方向")
    style_img = cv2.imread(style_path)
    # MediaPipe: 优先裸甲图，回退原图
    style_dirs = {}
    if os.path.exists(style_nat):
        print(f"  Try natural: {style_nat}")
        style_dirs = mp_detect(cv2.imread(style_nat))
    if not style_dirs:
        style_dirs = mp_detect(style_img)
    if style_dirs:
        print(f"  Fingers: {sorted(style_dirs.keys())}")
    else:
        print("  MediaPipe failed on style image")
    style_nails, style_mask = sam3_extract(style_img, sam3, style_dirs)
    cv2.imwrite(f"{OUT}/step1_style_mask.png", style_mask)
    for i, n in enumerate(style_nails):
        fn = n.get("finger", ""); label = fn or f"nail{i}"
        cv2.imwrite(f"{OUT}/step1_{label}.png", n["rgba"])
        print(f"  {label}: saved")
    draw_contours(style_img, style_nails, style_dirs,
                  f"{OUT}/step1_style_contours.png", f"Style {style_stem}")

    # ── Step 2: Hand 图 MediaPipe + SAM3 ──
    print("\n[Step 2] Hand 图: MediaPipe方向 + SAM3分割")
    hand_img = cv2.imread(hand_path)
    hand_dirs = mp_detect(hand_img)
    hand_nails, hand_mask = sam3_extract(hand_img, sam3, hand_dirs)
    cv2.imwrite(f"{OUT}/step2_hand_mask.png", hand_mask)
    for i, n in enumerate(hand_nails):
        fn = n.get("finger", ""); label = fn or f"nail{i}"
        print(f"  {label}: cx={n['cx']:.0f}" + (f" angle={hand_dirs[fn]['angle']}°" if fn in hand_dirs else ""))
    draw_contours(hand_img, hand_nails, hand_dirs,
                  f"{OUT}/step2_hand_contours.png", f"Hand {hand_stem}")

    # ── Step 3: 试戴 ──
    print("\n[Step 3] 试戴: 旋转+DIP定位+面积缩放+mask裁剪")
    paired = set()
    for sn in style_nails:
        fn = sn.get("finger", "")
        if fn and fn in hand_dirs: paired.add(fn)
    print(f"  配对手指: {sorted(paired)}")
    wear(style_nails, hand_dirs, style_dirs, hand_img, hand_nails,
         f"{OUT}/result_{style_stem}_to_{hand_stem}.png")

    print(f"\nDone → {OUT}")
    for f in sorted(os.listdir(OUT)):
        sz = os.path.getsize(os.path.join(OUT, f))
        print(f"  {f} ({sz/1024:.0f}KB)")


if __name__ == "__main__":
    main()
