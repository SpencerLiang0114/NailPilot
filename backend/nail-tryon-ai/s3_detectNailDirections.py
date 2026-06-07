"""
z2_extractNailV4.py — 修复手指与指甲对应顺序问题
确保 MediaPipe 的手指角度与 SAM3 的指甲纹理正确对应
"""

import os, cv2, numpy as np
from math import asin, degrees, sqrt, radians
from pathlib import Path
from ultralytics.models.sam import SAM3SemanticPredictor

STYLE_DIR = "./style"
STYLE_NATURAL = "./s2_style_natural"
OUT_DIR = "./s3_nail_Direction"
SAM3_WT = "./sys/sam3_weights/sam3.pt"
BPE_PATH = "./sys/bpe/bpe_simple_vocab_16e6.txt.gz"
LM_TASK = "./hand_landmarker.task"

NAIL_PROMPTS = ["nail", "fingernail", "fingernails"]

FINGER_DIPS = [3, 7, 11, 15, 19]
FINGER_TIPS = [4, 8, 12, 16, 20]


def lkGetP2Pangle(x1, y1, x2, y2):
    """0-360° 逆时针：0°=右 90°=上 180°=左 270°=下"""
    dx = x2 - x1
    dy = y2 - y1
    Length = sqrt(dx ** 2 + dy ** 2)
    if Length == 0: return 0.0
    if y1 == y2 and dx > 0: return 0.0
    if x1 == x2 and dy < 0: return 90.0
    if y1 == y2 and dx < 0: return 180.0
    if x1 == x2 and dy > 0: return 270.0
    deg = degrees(asin(abs(dy) / Length))
    if dx > 0 and dy < 0:
        return deg
    elif dx < 0 and dy < 0:
        return 180 - deg
    elif dx < 0 and dy > 0:
        return 180 + deg
    else:
        return 360 - deg


def mirror_angle(angle):
    """
    将角度进行镜像转换（用于左右手对称）
    假设原始角度是左手坐标系，镜像后得到右手坐标系的角度
    例如：原角度 45°（右上）→ 镜像后 135°（左上）
    """
    # 镜像转换：angle_new = 180 - angle (模360)
    mirrored = (180 - angle) % 360
    return mirrored


def load_sam3():
    return SAM3SemanticPredictor(
        bpe_path=BPE_PATH, overrides=dict(conf=0.2, task="segment",
                                          mode="predict", model=SAM3_WT, half=False,
                                          device="cpu", save=False, verbose=False))


def get_mediapipe_diptip(img_bgr):
    """
    返回 [(tip_x,tip_y,dip_x,dip_y,angle), ...]
    顺序: [thumb, index, middle, ring, pinky]
    """
    import mediapipe as mp
    from mediapipe.tasks import python as mpt
    from mediapipe.tasks.python import vision
    h, w = img_bgr.shape[:2]
    for conf in [0.3, 0.2, 0.1, 0.05]:
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB,
                          data=cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
        opt = vision.HandLandmarkerOptions(
            base_options=mpt.BaseOptions(model_asset_path=LM_TASK),
            num_hands=2, min_hand_detection_confidence=conf)
        det = vision.HandLandmarker.create_from_options(opt)
        res = det.detect(mp_img);
        det.close()
        if res and res.hand_landmarks:
            hand_lms = res.hand_landmarks[0]
            results = []
            for dip_idx, tip_idx in zip(FINGER_DIPS, FINGER_TIPS):
                dip = hand_lms[dip_idx]
                tip = hand_lms[tip_idx]
                tx, ty = int(tip.x * w), int(tip.y * h)
                dx, dy = int(dip.x * w), int(dip.y * h)
                angle = lkGetP2Pangle(dx, dy, tx, ty)
                results.append((tx, ty, dx, dy, angle))
            return results
    return None


def get_nail_masks(img_bgr):
    """返回 [(rgba, cx, cy), ...]，按 x 坐标排序"""
    h, w = img_bgr.shape[:2]
    predictor = load_sam3()
    predictor.set_image(img_bgr)

    all_masks = []
    for prompt in NAIL_PROMPTS:
        try:
            res = predictor(text=[prompt])
            if res and res[0].masks is not None:
                for mt in res[0].masks.data:
                    m = mt.cpu().numpy()
                    mbin = (m > 0.5).astype(np.uint8) * 255
                    m_rs = cv2.resize(mbin, (w, h), interpolation=cv2.INTER_NEAREST)
                    if cv2.countNonZero(m_rs) > 200:
                        all_masks.append(m_rs)
        except:
            continue

    if not all_masks: return []
    combined = np.zeros((h, w), dtype=np.uint8)
    for m in all_masks: combined = cv2.bitwise_or(combined, m)
    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    num_l, labels, stats, _ = cv2.connectedComponentsWithStats(combined, 8)

    nails = []
    for i in range(1, num_l):
        area = stats[i, cv2.CC_STAT_AREA]
        if area < 200 or area > 100000: continue
        x1, y1 = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP]
        x2 = x1 + stats[i, cv2.CC_STAT_WIDTH]
        y2 = y1 + stats[i, cv2.CC_STAT_HEIGHT]
        nail_mask = (labels == i).astype(np.uint8) * 255
        nail_mask_crop = nail_mask[y1:y2 + 1, x1:x2 + 1]
        nail_img_crop = img_bgr[y1:y2 + 1, x1:x2 + 1].copy()
        nail_rgba = cv2.cvtColor(nail_img_crop, cv2.COLOR_BGR2BGRA)
        nail_rgba[:, :, 3] = nail_mask_crop
        ys, xs = np.where(nail_mask_crop > 0)
        nails.append({"rgba": nail_rgba, "cx": xs.mean() + x1, "cy": ys.mean() + y1})
    nails.sort(key=lambda n: n["cx"])
    return nails


def match_nails_to_fingers(nails, mp_data):
    """
    根据 MediaPipe 手指 dip 的 x 坐标，将 nail 与 finger 正确配对
    mp_data 顺序: [thumb, index, middle, ring, pinky]
    返回: [(nail_rgba, angle), ...] 按 thumb→pinky 顺序

    修复：当拇指在右侧（需要反转顺序）时，角度也要进行镜像转换
    """
    if not mp_data or not nails:
        return []

    # 取 MediaPipe 各手指 dip_x
    mp_xs = [d[2] for d in mp_data]  # dip_x
    # 判断拇指在左还是右
    thumb_is_left = mp_xs[0] < mp_xs[4]  # thumb.dip_x < pinky.dip_x

    result = []
    for i in range(min(len(nails), len(mp_data))):
        if thumb_is_left:
            # 拇指在左：nail 按 x 排序 = thumb→pinky，直接对应，角度无需转换
            nail = nails[i]
            angle = mp_data[i][4]  # 角度保持不变
        else:
            # 拇指在右：nail 按 x 排序 = pinky→thumb，需要反转
            # 同时对应的角度也需要镜像转换（因为镜像手的方向变了）
            nail = nails[len(nails) - 1 - i]
            original_angle = mp_data[i][4]
            angle = mirror_angle(original_angle)  # 关键修复：角度镜像转换
        result.append((nail["rgba"], angle))
    return result


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    style_files = sorted(Path(STYLE_DIR).glob("*.png"))
    print(f"共 {len(style_files)} 款美甲\n")

    total_nails = 0
    for sf in style_files:
        stem = sf.stem
        print(f"[{stem}]", end=" ", flush=True)

        img = cv2.imread(str(sf))
        if img is None: print("❌ 读取失败"); continue

        # 1. MediaPipe 获取五指方向
        nat_path = Path(STYLE_NATURAL) / f"{stem}_natural.png"
        mp_data = None
        if nat_path.exists():
            nat_img = cv2.imread(str(nat_path))
            if nat_img is not None:
                mp_data = get_mediapipe_diptip(nat_img)
        if mp_data is None:
            mp_data = get_mediapipe_diptip(img)

        # 2. SAM3 提取指甲纹理
        nails = get_nail_masks(img)
        if not nails:
            print("❌ 无指甲");
            continue

        # 3. 正确配对指甲与手指
        matched = match_nails_to_fingers(nails, mp_data)
        if not matched:
            print("❌ 配对失败");
            continue

        n = min(len(matched), 5)

        # 额外调试信息：显示角度转换情况
        thumb_pos = "左手" if (mp_data and mp_data[0][2] < mp_data[4][2]) else "右手"

        for i in range(n):
            rgba, angle = matched[i]
            png_name = f"{stem}_nail{i + 1}.png"
            cv2.imwrite(str(Path(OUT_DIR) / png_name), rgba)
            txt_name = f"{stem}_nail{i + 1}_angle.txt"
            with open(Path(OUT_DIR) / txt_name, "w") as f:
                f.write(f"{angle:.1f}\n")

        total_nails += n
        info = f"✅ {n}个 ({thumb_pos})"
        if mp_data:
            # 显示实际写入的角度值
            angles_str = ",".join(f"{matched[i][1]:.0f}" for i in range(n))
            info += f" [{angles_str}]"
        else:
            info += " mp=❌"
        print(info)

    print(f"\n{'=' * 50}")
    print(f"完成! 共 {total_nails} 个指甲 → {OUT_DIR}")


if __name__ == "__main__":
    main()
