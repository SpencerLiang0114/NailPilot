"""
s11_extractNailV2.py — 分割手掌图中各手指甲，按大拇指→小拇指保存为 fingernail1~5.png

输入：./s6_hands_natural/*.png
输出：./s11_getFingerNail/<stem>/fingernail1.png ~ fingernail5.png
"""

import os
import sys
import cv2
import math
import numpy as np
from pathlib import Path

# ── 路径配置 ──
SRC_DIR   = "./s6_hands_natural"
OUT_DIR   = "./s11_getFingerNail"
SAM3_WT   = "./sys/sam3_weights/sam3.pt"
BPE_PATH  = "./sys/bpe/bpe_simple_vocab_16e6.txt.gz"

# ── 导入 SAM3（ultralytics 封装） ──
from ultralytics.models.sam import SAM3SemanticPredictor

# ── 导入 MediaPipe（旧版 solutions API，0.10.9 可用） ──
import mediapipe as mp
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

# 手指指尖索引（MediaPipe 21 点）
FINGER_TIPS = [4, 8, 12, 16, 20]  # thumb, index, middle, ring, pinky


def ensure_dirs(stem: str):
    """为每张图创建输出子目录"""
    d = Path(OUT_DIR) / stem
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_predictor():
    """加载 SAM3 语义分割器"""
    return SAM3SemanticPredictor(
        bpe_path=BPE_PATH,
        overrides=dict(
            conf=0.2,
            task="segment",
            mode="predict",
            model=SAM3_WT,
            half=False,
            device="cpu",
            save=False,
            verbose=False,
        ),
    )


def detect_hand_landmarks(image_bgr):
    """
    用 MediaPipe Hands 检测手部关键点
    返回: (landmarks_list, handedness_str) 或 (None, None)
    landmarks_list: 21 个 (x, y) 归一化坐标（图像坐标系，非 MediaPipe 的 y-flip）
    handedness_str: "Left" 或 "Right"
    """
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    h, w = image_bgr.shape[:2]

    with mp_hands.Hands(
        static_image_mode=True,
        max_num_hands=1,
        min_detection_confidence=0.5,
    ) as hands:
        results = hands.process(image_rgb)

    if not results.multi_hand_landmarks:
        return None, None

    hand_landmarks = results.multi_hand_landmarks[0]
    handedness = results.multi_handedness[0].classification[0].label  # "Left" / "Right"

    # 提取 21 个关键点（x,y 是归一化 0~1，转成像素坐标）
    landmarks = []
    for lm in hand_landmarks.landmark:
        landmarks.append((lm.x * w, lm.y * h))

    return landmarks, handedness


def order_fingers_thumb_to_pinky(landmarks, handedness):
    """
    根据手部关键点和左右手判断，返回从大拇指→小拇指的指尖索引排序。
    原理：以手腕→中指指尖为手的主轴，求垂直方向投影，按左右手特性排序。
    返回: list of 5 ints，每个是 FINGER_TIPS 中的索引在原始列表中的位置
          即返回的是 [thumb_idx, index_idx, middle_idx, ring_idx, pinky_idx]
          其中 thumb_idx 等是 0~4，对应 FINGER_TIPS[thumb_idx] = 4（大拇指指尖）
    """
    wrist = np.array(landmarks[0])
    middle_tip = np.array(landmarks[12])

    hand_dir = middle_tip - wrist
    hand_dir_len = np.linalg.norm(hand_dir)
    if hand_dir_len < 1e-6:
        # 退化情况，默认手指朝上
        hand_dir = np.array([0.0, -1.0])
    else:
        hand_dir = hand_dir / hand_dir_len

    # 主轴逆时针旋转 90° 得到“右侧”方向（从手腕往指尖看，右手大拇指所在侧）
    perp = np.array([-hand_dir[1], hand_dir[0]])

    # 计算每个指尖在该垂直方向上的投影
    projections = []
    for tip_idx in FINGER_TIPS:
        tip = np.array(landmarks[tip_idx])
        vec = tip - wrist
        proj = np.dot(vec, perp)
        projections.append(proj)

    projections = np.array(projections)

    if handedness == "Right":
        # 右手：大拇指在右侧，投影最大
        order = np.argsort(projections)[::-1]  # 大到小
    else:
        # 左手：大拇指在左侧，投影最小
        order = np.argsort(projections)        # 小到大

    return order.tolist()  # 5 个索引，分别对应 thumb, index, middle, ring, pinky


def segment_nails_with_sam3(image_bgr, predictor):
    """
    用 SAM3 文本提示分割所有指甲，返回合并后的二值掩码 (h, w)
    """
    h, w = image_bgr.shape[:2]
    prompts = ["nail", "fingernail", "nail polish", "fingernails"]

    predictor.set_image(image_bgr)

    all_masks = []
    for prompt in prompts:
        try:
            results = predictor(text=[prompt])
            if results and results[0].masks is not None:
                for mt in results[0].masks.data:
                    mask = mt.cpu().numpy()
                    mask_bin = (mask > 0.5).astype(np.uint8) * 255
                    mask_rs = cv2.resize(mask_bin, (w, h), interpolation=cv2.INTER_NEAREST)
                    if cv2.countNonZero(mask_rs) > 50:
                        all_masks.append(mask_rs)
        except Exception as e:
            print(f"    SAM3 prompt '{prompt}' 失败: {e}")
            continue

    if not all_masks:
        return None

    # 合并所有掩码
    combined = np.zeros((h, w), dtype=np.uint8)
    for m in all_masks:
        combined = cv2.bitwise_or(combined, m)

    # 形态学去噪
    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

    # 只保留面积合适的连通域
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(combined, connectivity=8)
    final_mask = np.zeros((h, w), dtype=np.uint8)
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if 100 < area < 50000:
            final_mask[labels == i] = 255

    return final_mask


def split_nail_mask_by_fingers(combined_mask, landmarks, finger_order):
    """
    将合并的指甲掩码按手指切分为 5 个独立掩码。
    策略：
      1. 对合并掩码做连通域分析
      2. 每个连通域的质心分配给最近的指尖
      3. 同一指尖可能有多个连通域（指甲断裂等情况），合并之
    返回: list of 5 np.ndarray，按 finger_order 的语义顺序排列
          即 [thumb_mask, index_mask, middle_mask, ring_mask, pinky_mask]
    """
    h, w = combined_mask.shape

    # 连通域分析
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        combined_mask, connectivity=8
    )

    # 收集有效连通域（过滤过小/过大的）
    components = []
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if 50 < area < 50000:
            components.append({
                'label': i,
                'area': area,
                'centroid': centroids[i],  # (cx, cy)
                'mask': (labels == i).astype(np.uint8) * 255,
            })

    if not components:
        return [np.zeros((h, w), dtype=np.uint8) for _ in range(5)]

    # 指尖像素坐标
    tip_positions = [np.array(landmarks[tip_idx]) for tip_idx in FINGER_TIPS]

    # 初始化 5 个手指的掩码
    finger_masks = [np.zeros((h, w), dtype=np.uint8) for _ in range(5)]

    # 每个连通域分配给最近的指尖（按欧氏距离）
    for comp in components:
        cx, cy = comp['centroid']
        # 计算到 5 个指尖的距离
        distances = [math.hypot(cx - tx, cy - ty) for tx, ty in tip_positions]
        nearest_finger_idx = int(np.argmin(distances))  # 0~4，对应 FINGER_TIPS 中的位置

        # 合并到该手指的掩码中
        finger_masks[nearest_finger_idx] = cv2.bitwise_or(
            finger_masks[nearest_finger_idx], comp['mask']
        )

    # 按 finger_order 重新排列：从 thumb→index→middle→ring→pinky
    # finger_order[i] 表示“第 i 个手指（0=thumb, 1=index, ...）在 FINGER_TIPS 中的原始索引”
    # 所以 finger_masks[finger_order[0]] 是 thumb 的掩码
    ordered_masks = [finger_masks[finger_order[i]] for i in range(5)]

    return ordered_masks


def save_nail_masks(stem, ordered_masks):
    """
    按大拇指→小拇指顺序保存 fingernail1.png ~ fingernail5.png
    ordered_masks[0] = thumb, ordered_masks[1] = index, ..., ordered_masks[4] = pinky
    """
    out_dir = ensure_dirs(stem)
    names = ["thumb", "index", "middle", "ring", "pinky"]

    saved = []
    for i, mask in enumerate(ordered_masks):
        filename = f"fingernail{i+1}.png"  # 1=thumb, 5=pinky
        path = out_dir / filename
        cv2.imwrite(str(path), mask)
        area = cv2.countNonZero(mask)
        saved.append(f"{names[i]}={area}px")

    print(f"    → 保存: {', '.join(saved)}")
    return out_dir


def process_one(img_path: Path, predictor):
    stem = img_path.stem
    print(f"\n[{stem}]")

    # ── 1. 读取图片 ──
    image_bgr = cv2.imread(str(img_path))
    if image_bgr is None:
        print(f"  ❌ 无法读取图片")
        return False

    # ── 2. MediaPipe 检测手部关键点 ──
    landmarks, handedness = detect_hand_landmarks(image_bgr)
    if landmarks is None:
        print(f"  ❌ 未检测到手部")
        return False
    print(f"  ✋ 检测到手部: {handedness} hand, 21 landmarks")

    # ── 3. 确定手指顺序（大拇指→小拇指） ──
    finger_order = order_fingers_thumb_to_pinky(landmarks, handedness)
    names = ["thumb", "index", "middle", "ring", "pinky"]
    order_str = ", ".join([names[i] for i in finger_order])
    print(f"  📋 手指顺序: {order_str}")

    # ── 4. SAM3 分割指甲 ──
    print(f"  🔍 SAM3 分割指甲...")
    combined_mask = segment_nails_with_sam3(image_bgr, predictor)
    if combined_mask is None or cv2.countNonZero(combined_mask) == 0:
        print(f"  ❌ SAM3 未检测到指甲")
        return False
    print(f"  ✅ SAM3 掩码面积: {cv2.countNonZero(combined_mask)} px")

    # ── 5. 按手指切分掩码 ──
    ordered_masks = split_nail_mask_by_fingers(combined_mask, landmarks, finger_order)

    # ── 6. 保存结果 ──
    out_dir = save_nail_masks(stem, ordered_masks)

    # ── 7. 保存可视化叠加图（可选） ──
    vis = image_bgr.copy()
    colors = [
        (0, 0, 255),    # thumb 红
        (0, 165, 255),  # index 橙
        (0, 255, 255),  # middle 黄
        (0, 255, 0),    # ring 绿
        (255, 0, 0),    # pinky 蓝
    ]
    for i, mask in enumerate(ordered_masks):
        if cv2.countNonZero(mask) > 0:
            # 半透明叠加
            overlay = vis.copy()
            overlay[mask > 0] = colors[i]
            vis = cv2.addWeighted(vis, 0.7, overlay, 0.3, 0)
            # 轮廓
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(vis, contours, -1, colors[i], 2)
            # 标签
            if contours:
                M = cv2.moments(contours[0])
                if M["m00"] > 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    cv2.putText(vis, f"{i+1}:{names[finger_order[i]]}", (cx-20, cy),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, colors[i], 2)

    cv2.imwrite(str(out_dir / "visualization.png"), vis)
    print(f"  🖼 可视化已保存")

    return True


def main():
    print("=" * 60)
    print("  s11_extractNailV2 — 按大拇指→小拇指分割指甲")
    print("=" * 60)

    predictor = load_predictor()
    print(f"✅ SAM3 预测器加载完成")

    images = sorted(Path(SRC_DIR).glob("*.png"))
    print(f"\n共 {len(images)} 张图片\n")

    success = 0
    for img_path in images:
        if process_one(img_path, predictor):
            success += 1

    print(f"\n{'='*60}")
    print(f"完成: {success}/{len(images)} 张图片处理成功")
    print(f"输出目录: {OUT_DIR}")
    print(f"每张图的 fingernail1.png~fingernail5.png 保存在各自的子文件夹中")


if __name__ == "__main__":
    main()
