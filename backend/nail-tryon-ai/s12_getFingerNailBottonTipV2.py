"""
s12_getFingerNailBottonTipV2.py
获取每个指甲掩码在手指方向上的最低点和最高点（T轴极值点），
并在这两个点上画红色实心圆。

V2 改动：
  - 读取路径改为 s11_getFingerNail/<stem>/fingernail1~5.png（子文件夹结构）
  - 角度文件仍从 s7_hands_finger_direction/<stem>_angle.txt 读取
  - 输出到 s12_getFingerNailBottonTip/<stem>/fingernail*_annotated.png
  - 支持批量处理多张手部图片

输入:
  ./s11_getFingerNail/<stem>/fingernail1~5.png        # 指甲掩码(二值)
  ./s7_hands_finger_direction/<stem>_angle.txt       # 手指方向角度(度)

输出:
  ./s12_getFingerNailBottonTip/<stem>/fingernail*_annotated.png
  ./s12_getFingerNailBottonTip/<stem>/extreme_points.csv
"""

import os
import sys
import cv2
import numpy as np
from pathlib import Path

# ─── 路径配置 ─────────────────────────────────────────────
MASK_BASE_DIR = r"./s11_getFingerNail"
ANGLE_DIR     = r"./s7_hands_finger_direction"
OUTPUT_DIR    = r"./s12_getFingerNailBottonTip"

FINGER_NAMES = ["thumb", "index", "middle", "ring", "pinky"]

# 圆半径（像素）
CIRCLE_RADIUS_PX = 5
# 比例模式：设为 True 则半径 = rel_ratio * 图像对角线
USE_RELATIVE_RADIUS = False
REL_RATIO = 0.02   # 0.02 = 2% 的对角线长度


def read_finger_angles(filepath):
    """读取手指角度文件，返回角度列表 [thumb, index, middle, ring, pinky]。"""
    angles = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                angles.append(float(line))
    return angles


def get_contour_T_extremes(contour_pts, angle_deg):
    """在轮廓点上计算T投影，返回T最小和T最大的点坐标。

    T = x*cos(θ) - y*sin(θ)   (图像坐标系 y向下)

    Args:
        contour_pts: (N, 2) ndarray [x, y] 轮廓点
        angle_deg: 手指方向角度（度）

    Returns:
        bottom_pt: (x, y) int  T值最小的点
        top_pt:    (x, y) int  T值最大的点
    """
    angle_rad = np.radians(angle_deg)
    cos_a = np.cos(angle_rad)
    sin_a = np.sin(angle_rad)

    # T投影
    T_vals = contour_pts[:, 0] * cos_a - contour_pts[:, 1] * sin_a

    bottom_idx = int(np.argmin(T_vals))
    top_idx = int(np.argmax(T_vals))

    bottom_pt = (int(contour_pts[bottom_idx, 0]), int(contour_pts[bottom_idx, 1]))
    top_pt    = (int(contour_pts[top_idx, 0]),    int(contour_pts[top_idx, 1]))

    return bottom_pt, top_pt


def compute_radius(mask_shape, use_relative=USE_RELATIVE_RADIUS,
                   rel_ratio=REL_RATIO, fallback_px=CIRCLE_RADIUS_PX):
    """计算圆半径。"""
    if not use_relative:
        return fallback_px
    h, w = mask_shape[:2]
    diag = np.sqrt(h * h + w * w)
    r = int(diag * rel_ratio)
    return max(1, r)


def draw_annotated_mask(mask_gray, bottom_pt, top_pt, radius):
    """在掩码图像上画红色实心圆标注最低点和最高点。

    Args:
        mask_gray:  (H, W) uint8 灰度掩码
        bottom_pt:   (x, y) T最小点
        top_pt:      (x, y) T最大点
        radius:      圆半径（像素）

    Returns:
        result_bgr: (H, W, 3) uint8 BGR 标注图像
    """
    if len(mask_gray.shape) == 2:
        vis = cv2.cvtColor(mask_gray, cv2.COLOR_GRAY2BGR)
    else:
        vis = mask_gray.copy()

    red = (0, 0, 255)

    if bottom_pt is not None:
        cv2.circle(vis, bottom_pt, radius, red, -1)
        cv2.putText(vis, "bottom",
                     (bottom_pt[0] + radius + 3, bottom_pt[1] + 5),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.5, red, 1)

    if top_pt is not None:
        cv2.circle(vis, top_pt, radius, red, -1)
        cv2.putText(vis, "top",
                     (top_pt[0] + radius + 3, top_pt[1] + 5),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.5, red, 1)

    return vis


def process_one_hand(stem, mask_base_dir, angle_dir, output_dir):
    """
    处理单张手部图片对应的 5 个指甲掩码。
    返回 True/False 表示成功/失败。
    """
    mask_dir = Path(mask_base_dir) / stem
    out_dir  = Path(output_dir) / stem
    out_dir.mkdir(parents=True, exist_ok=True)

    angle_file = Path(angle_dir) / f"{stem}_angle.txt"
    if not angle_file.exists():
        print(f"  ❌ 角度文件不存在: {angle_file}")
        return False

    angles = read_finger_angles(str(angle_file))
    if len(angles) < 5:
        print(f"  ⚠ 角度文件只有 {len(angles)} 个角度，期望 5 个")
        angles += [0.0] * (5 - len(angles))

    print(f"  📐 角度: " + ", ".join([f"{a:.1f}°" for a in angles[:5]]))

    results = []

    for i in range(5):
        finger_name = FINGER_NAMES[i]
        angle = angles[i]

        mask_path = mask_dir / f"fingernail{i+1}.png"
        if not mask_path.exists():
            print(f"    [{finger_name}] ⚠ 掩码不存在: {mask_path}")
            results.append(None)
            continue

        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if mask is None:
            print(f"    [{finger_name}] ❌ 无法读取: {mask_path}")
            results.append(None)
            continue

        _, binary = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if not contours:
            print(f"    [{finger_name}] ⚠ 未找到轮廓")
            results.append(None)
            continue

        contour = max(contours, key=cv2.contourArea).reshape(-1, 2)

        bottom_pt, top_pt = get_contour_T_extremes(contour, angle)

        print(f"    [{finger_name}] angle={angle:.1f}°  bottom={bottom_pt}  top={top_pt}")

        radius = compute_radius(mask.shape)
        result_img = draw_annotated_mask(mask, bottom_pt, top_pt, radius)

        out_name = f"fingernail{i+1}_annotated.png"
        out_path = out_dir / out_name
        cv2.imwrite(str(out_path), result_img)

        results.append({
            "finger":   finger_name,
            "angle":    angle,
            "bottom_pt": bottom_pt,
            "top_pt":    top_pt,
            "output":    str(out_path),
        })

    # 保存该手的极值点 CSV
    csv_path = out_dir / "extreme_points.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("手指,角度,bottom_x,bottom_y,top_x,top_y\n")
        for r in results:
            if r is not None:
                f.write(f"{r['finger']},{r['angle']:.1f},"
                        f"{r['bottom_pt'][0]},{r['bottom_pt'][1]},"
                        f"{r['top_pt'][0]},{r['top_pt'][1]}\n")

    n_done = sum(1 for r in results if r is not None)
    print(f"    ✅ {n_done}/5 个手指处理完成 → {out_dir}")
    return True


def main():
    print("=" * 65)
    print("  s12_getFingerNailBottonTipV2 — T轴极值点标注")
    print("=" * 65)

    mask_base = Path(MASK_BASE_DIR)
    if not mask_base.exists():
        print(f"[FATAL] 掩码根目录不存在: {MASK_BASE_DIR}")
        sys.exit(1)

    # 扫描 s11_getFingerNail 下的所有子文件夹，只保留含 fingernail1.png 的
    subdirs = sorted([
        d for d in mask_base.iterdir()
        if d.is_dir() and (d / "fingernail1.png").exists()
    ])
    if not subdirs:
        # 兼容：如果 s11_getFingerNail 下直接有 fingernail*.png，也处理
        pngs = sorted(mask_base.glob("fingernail*.png"))
        if pngs:
            print("⚠ 未找到子文件夹，尝试直接处理掩码文件（旧结构）")
            # 用 s11_getFingerNail 作为 stem
            process_one_hand("a13_natural", MASK_BASE_DIR, ANGLE_DIR, OUTPUT_DIR)
    else:
        print(f"\n找到 {len(subdirs)} 张手部图片的掩码文件夹:\n")
        for sd in subdirs:
            stem = sd.name
            print(f"\n── 处理: {stem} ──")
            process_one_hand(stem, MASK_BASE_DIR, ANGLE_DIR, OUTPUT_DIR)

    print(f"\n{'='*65}")
    print(f"全部完成! 输出目录: {os.path.abspath(OUTPUT_DIR)}")
    print("=" * 65)


if __name__ == "__main__":
    main()
