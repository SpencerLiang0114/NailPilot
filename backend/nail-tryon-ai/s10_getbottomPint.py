"""
s10_getbottomPint.py
对 s9 旋转后的美甲图像，以手指方向角度为数轴 T，
在美甲边界上找到 T 轴投影的最高点和最低点，
并用红色实心圆标记。

算法:
  1. 读取旋转后美甲图像 (s9_rotNail2MatchFingerDirection_v2/)
  2. 读取手指方向角度 (a13_natural_angle.txt)
  3. 提取美甲前景轮廓（边界点）
  4. 将所有边界点投影到手指方向数轴 T 上
  5. 找到投影值最大（T最高点）和最小（T最低点）的边界点
  6. 在这两个点上画红色实心圆

输入:
  ./s9_rotNail2MatchFingerDirection_v2/a2_nail1~5_rotated.png  # 旋转后美甲
  ./s7_hands_finger_direction/a13_natural_angle.txt             # 手指方向(5行)

输出:
  ./s10_getbottomPint/a2_nail1~5_pint.png       # 标记了最高/最低点的图像
  ./s10_getbottomPint/bottom_pint_info.csv      # 坐标信息
"""

import os
import sys
import cv2
import numpy as np

# ─── 路径配置 ─────────────────────────────────────────────
NAIL_DIR = r"./s9_rotNail2MatchFingerDirection_v2"
FINGER_ANGLE_FILE = r"./s7_hands_finger_direction/a13_natural_angle.txt"
OUTPUT_DIR = r"./s10_getbottomPint"

FINGER_NAMES = ["thumb", "index", "middle", "ring", "pinky"]


def read_finger_angles(finger_path):
    """读取手指自然方向角度。返回 list[float] — thumb~pinky 的手指方向角度"""
    angles = []
    with open(finger_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                angles.append(float(line))
    return angles


def get_boundary_points(image_bgra):
    """提取美甲前景的边界点（轮廓上的像素坐标）。
    
    Args:
        image_bgra: BGRA格式图像
    
    Returns:
        boundary_pts: (N, 2) ndarray — [x, y] 边界点坐标
    """
    # 获取前景mask
    if image_bgra.shape[2] >= 4:
        alpha = image_bgra[:, :, 3]
        mask = (alpha > 10).astype(np.uint8) * 255
    else:
        gray = cv2.cvtColor(image_bgra, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 20, 255, cv2.THRESH_BINARY)
    
    # 找轮廓（只取外轮廓）
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    
    if len(contours) == 0:
        return None
    
    # 取面积最大的轮廓
    largest = max(contours, key=cv2.contourArea)
    
    # 轮廓点 shape: (N, 1, 2) → 展平为 (N, 2): [x, y]
    boundary_pts = largest.reshape(-1, 2)
    
    return boundary_pts


def project_on_axis(points, angle_deg):
    """将点投影到以指定角度为数轴 T 的方向上。
    
    在图像坐标系中 (x→右, y→下):
      T 轴方向: 从水平轴逆时针 angle_deg 度
      单位向量: (cos(θ), -sin(θ))
      投影值 T = x*cos(θ) - y*sin(θ)
    
    Args:
        points: (N, 2) ndarray — [x, y] 坐标
        angle_deg: T 轴方向角度（度，从水平轴逆时针）
    
    Returns:
        t_values: (N,) ndarray — 各点在 T 轴上的投影值
    """
    angle_rad = np.radians(angle_deg)
    cos_a = np.cos(angle_rad)
    sin_a = np.sin(angle_rad)
    
    # T = x*cos(θ) + y*(-sin(θ))
    t_values = points[:, 0] * cos_a - points[:, 1] * sin_a
    
    return t_values


def find_extreme_points(boundary_pts, t_values):
    """找到 T 轴上的最高点（最大投影）和最低点（最小投影）。
    
    Args:
        boundary_pts: (N, 2) — 边界点坐标 [x, y]
        t_values: (N,) — T 轴投影值
    
    Returns:
        pt_max: [x, y] — T 最高点（投影最大）
        pt_min: [x, y] — T 最低点（投影最小）
    """
    idx_max = np.argmax(t_values)
    idx_min = np.argmin(t_values)
    
    pt_max = boundary_pts[idx_max]
    pt_min = boundary_pts[idx_min]
    
    return pt_max, pt_min


def draw_marked_image(image_bgra, pt_max, pt_min, angle_deg, radius=5):
    """在原图上标记 T 轴最高点和最低点，并绘制 T 轴方向。
    
    Args:
        image_bgra: 原图 (BGRA)
        pt_max: [x, y] T 最高点
        pt_min: [x, y] T 最低点
        angle_deg: T 轴方向角度
        radius: 圆半径（像素）
    
    Returns:
        marked: 标记后的图像 (BGRA)
    """
    marked = image_bgra.copy()
    h, w = marked.shape[:2]
    
    # ── 绘制 T 轴方向线（绿色虚线，贯穿图像中心） ──
    center_x = w / 2.0
    center_y = h / 2.0
    angle_rad = np.radians(angle_deg)
    
    # 方向向量
    dx = np.cos(angle_rad)
    dy = -np.sin(angle_rad)  # 图像坐标系中 y 向下
    
    # 延伸到图像边缘
    diag = np.sqrt(w**2 + h**2) / 2
    x1 = int(center_x - dx * diag)
    y1 = int(center_y - dy * diag)
    x2 = int(center_x + dx * diag)
    y2 = int(center_y + dy * diag)
    
    # 虚线
    for j in range(0, int(2 * diag), 12):
        seg_x1 = int(center_x + dx * (j - diag))
        seg_y1 = int(center_y + dy * (j - diag))
        seg_x2 = int(center_x + dx * (j - diag + 8))
        seg_y2 = int(center_y + dy * (j - diag + 8))
        cv2.line(marked, (seg_x1, seg_y1), (seg_x2, seg_y2), (0, 255, 0, 128), 1)
    
    # ── 画红色实心圆标记最高点 ──
    cv2.circle(marked, (int(pt_max[0]), int(pt_max[1])), radius, (0, 0, 255, 255), -1)
    # 白色外圈让标记更醒目
    cv2.circle(marked, (int(pt_max[0]), int(pt_max[1])), radius, (255, 255, 255, 255), 1)
    # 标注 "T_max"
    cv2.putText(marked, "T+", (int(pt_max[0]) + radius + 4, int(pt_max[1]) + 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255, 255), 2)
    
    # ── 画红色实心圆标记最低点 ──
    cv2.circle(marked, (int(pt_min[0]), int(pt_min[1])), radius, (0, 0, 255, 255), -1)
    cv2.circle(marked, (int(pt_min[0]), int(pt_min[1])), radius, (255, 255, 255, 255), 1)
    # 标注 "T_min"
    cv2.putText(marked, "T-", (int(pt_min[0]) + radius + 4, int(pt_min[1]) + 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255, 255), 2)
    
    # ── 显示角度信息 ──
    cv2.putText(marked, f"Angle: {angle_deg:.1f}", (8, 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255, 255), 2)
    
    return marked


def main():
    print("=" * 60)
    print("s10_getbottomPint: T轴最高/最低边界点标记")
    print("=" * 60)

    # ── 读取手指角度 ──
    finger_angles = read_finger_angles(FINGER_ANGLE_FILE)
    print(f"\n手指方向角度 (T轴): {finger_angles}")

    # ── 创建输出目录 ──
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ── 处理每张美甲 ──
    print(f"\n处理美甲图像:")
    print("-" * 60)

    records = []

    for i in range(5):
        img_name = f"a2_nail{i+1}_rotated.png"
        img_path = os.path.join(NAIL_DIR, img_name)
        
        if not os.path.exists(img_path):
            print(f"  [跳过] 文件不存在: {img_path}")
            continue

        finger_angle = finger_angles[i]
        finger_name = FINGER_NAMES[i]

        print(f"\n  {img_name} ({finger_name})")
        print(f"    T轴方向: {finger_angle:.1f}°")

        # 读取图像 (保持BGRA)
        img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            print(f"    [错误] 无法读取图像")
            continue

        h, w = img.shape[:2]
        print(f"    图像尺寸: {w}x{h}")

        # ── 1. 提取边界点 ──
        boundary_pts = get_boundary_points(img)
        if boundary_pts is None:
            print(f"    [警告] 未检测到轮廓，跳过")
            continue

        print(f"    边界点数: {len(boundary_pts)}")

        # ── 2. 投影到 T 轴 ──
        t_values = project_on_axis(boundary_pts, finger_angle)
        t_min_val = t_values.min()
        t_max_val = t_values.max()
        print(f"    T轴范围: [{t_min_val:.1f}, {t_max_val:.1f}]")
        print(f"    T轴跨度: {t_max_val - t_min_val:.1f}")

        # ── 3. 找最高点和最低点 ──
        pt_max, pt_min = find_extreme_points(boundary_pts, t_values)
        print(f"    T+ (最高点): ({pt_max[0]:.0f}, {pt_max[1]:.0f})  T={t_max_val:.1f}")
        print(f"    T- (最低点): ({pt_min[0]:.0f}, {pt_min[1]:.0f})  T={t_min_val:.1f}")

        # ── 4. 绘制标记图 ──
        # 半径: 图像短边的 1.5%，最小 3px
        radius = max(3, int(min(h, w) * 0.015))
        marked = draw_marked_image(img, pt_max, pt_min, finger_angle, radius=radius)

        # ── 5. 保存 ──
        out_path = os.path.join(OUTPUT_DIR, f"a2_nail{i+1}_pint.png")
        cv2.imwrite(out_path, marked)
        print(f"    已保存 → {out_path}")

        # ── 记录信息 ──
        records.append({
            "finger": finger_name,
            "angle": finger_angle,
            "T_min": t_min_val,
            "T_max": t_max_val,
            "T_span": t_max_val - t_min_val,
            "pt_min_x": pt_min[0],
            "pt_min_y": pt_min[1],
            "pt_max_x": pt_max[0],
            "pt_max_y": pt_max[1],
        })

    # ── 保存坐标报告 ──
    info_path = os.path.join(OUTPUT_DIR, "bottom_pint_info.csv")
    with open(info_path, "w", encoding="utf-8") as f:
        f.write("手指,T轴角度,T_min,T_max,T_span,最低点x,最低点y,最高点x,最高点y\n")
        for r in records:
            f.write(f"{r['finger']},{r['angle']:.1f},{r['T_min']:.1f},{r['T_max']:.1f},{r['T_span']:.1f},{r['pt_min_x']:.0f},{r['pt_min_y']:.0f},{r['pt_max_x']:.0f},{r['pt_max_y']:.0f}\n")

    print(f"\n坐标报告已保存 → {info_path}")
    print(f"\n{'=' * 60}")
    print(f"完成! 共处理 {len(records)} 张美甲")
    print(f"结果保存至: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
