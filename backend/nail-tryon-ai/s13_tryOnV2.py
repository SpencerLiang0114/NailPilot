"""
s13_tryOnV2.py
美甲试戴：将旋转后的美甲图像与手部图像对应指甲区域对齐合成。

V2 改动：
  - s12 extreme_points.csv 路径改为 s12_getFingerNailBottonTip/<stem>/extreme_points.csv
  - 手部图片路径改为 s6_hands_natural/<stem>.png
  - 手指角度文件路径改为 s7_hands_finger_direction/<stem>_angle.txt
  - 输出改为 s13_tryOn/<stem>/ 子文件夹
  - 支持批量处理（扫描 s12 输出文件夹，对每个 stem 执行试戴）

对齐策略:
  1. 从 s10_getbottomPint 读取各美甲的 T_min 最低点（美甲"根部"）
  2. 从 s12_getFingerNailBottonTip 读取各指甲掩码的 bottom 最低点（手部"根部"）
  3. 将美甲根部与手部根部对齐：paste_xy = hand_bottom - nail_bottom
  4. Alpha 混合合成到手部图像上

输入:
  ./s9_rotNail2MatchFingerDirection_v2/a2_nail1~5_rotated.png  # 旋转后美甲
  ./s10_getbottomPint/bottom_pint_info.csv                      # 美甲T_min点
  ./s12_getFingerNailBottonTip/<stem>/extreme_points.csv        # 手部掩码bottom点
  ./s6_hands_natural/<stem>.png                                 # 手部图像
  ./s7_hands_finger_direction/<stem>_angle.txt                  # 手指方向角度

输出:
  ./s13_tryOn/<stem>/<stem>_tryon.png         # 最终试戴合成结果
  ./s13_tryOn/<stem>/<stem>_tryon_debug.png   # 带标注的调试图像
  ./s13_tryOn/<stem>/alignment_info.csv        # 对齐信息汇总
"""

import os
import sys
import csv
import cv2
import numpy as np
from pathlib import Path

# ─── 路径配置 ─────────────────────────────────────────────
NAIL_DIR        = r"./s9_rotNail2MatchFingerDirection_v2"
NAIL_PINT_CSV   = r"./s10_getbottomPint/bottom_pint_info.csv"
S12_DIR         = r"./s12_getFingerNailBottonTip"
HAND_DIR        = r"./s6_hands_natural"
ANGLE_DIR       = r"./s7_hands_finger_direction"
OUTPUT_DIR      = r"./s13_tryOn"

FINGER_NAMES = ["thumb", "index", "middle", "ring", "pinky"]
COLORS = [
    (255, 0, 0),     # thumb: 蓝色
    (0, 255, 0),     # index: 绿色
    (0, 0, 255),     # middle: 红色
    (0, 255, 255),   # ring: 黄色
    (255, 0, 255),   # pinky: 品红
]


# ═══════════════════════════════════════════════════════════
#  工具函数
# ═══════════════════════════════════════════════════════════

def read_finger_angles(filepath):
    """读取手指自然方向角度。"""
    angles = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                angles.append(float(line))
    return angles


def read_nail_pint_info(csv_path):
    """从 s10 bottom_pint_info.csv 读取各美甲的 T_min 最低点。

    CSV 列: 手指,T轴角度,T_min,T_max,T_span,最低点x,最低点y,最高点x,最高点y

    Returns:
        list[dict]: 每个手指的 {finger, angle, pt_min: (x,y), pt_max: (x,y)}
    """
    records = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append({
                "finger": row["手指"],
                "angle": float(row["T轴角度"]),
                "pt_min": (int(float(row["最低点x"])), int(float(row["最低点y"]))),
                "pt_max": (int(float(row["最高点x"])), int(float(row["最高点y"]))),
            })
    return records


def read_mask_extreme_info(csv_path):
    """从 s12 extreme_points.csv 读取各指甲掩码的 bottom 点。

    CSV 列: 手指,角度,bottom_x,bottom_y,top_x,top_y

    Returns:
        list[dict]: 每个手指的 {finger, angle, pt_bottom: (x,y), pt_top: (x,y)}
    """
    records = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append({
                "finger":    row["手指"],
                "angle":     float(row["角度"]),
                "pt_bottom": (int(float(row["bottom_x"])), int(float(row["bottom_y"]))),
                "pt_top":    (int(float(row["top_x"])),    int(float(row["top_y"]))),
            })
    return records


def alpha_blend_onto(base_bgr, bgra, paste_x, paste_y):
    """将 RGBA 图像 alpha 混合到 BGR 底图上。

    Args:
        base_bgr: (H, W, 3) uint8  BGR 底图（原地修改并返回）
        bgra:     (H, W, 4) uint8  BGRA 前景
        paste_x:  int  粘贴左上角 x 坐标
        paste_y:  int  粘贴左上角 y 坐标

    Returns:
        base_bgr: 修改后的底图
    """
    h, w   = bgra.shape[:2]
    bh, bw = base_bgr.shape[:2]

    x0, y0 = paste_x, paste_y
    x1, y1 = x0 + w, y0 + h

    dx0, dy0 = max(x0, 0), max(y0, 0)
    dx1, dy1 = min(x1, bw), min(y1, bh)

    if dx1 <= dx0 or dy1 <= dy0:
        return base_bgr

    sx0 = dx0 - x0
    sy0 = dy0 - y0
    sx1 = sx0 + (dx1 - dx0)
    sy1 = sy0 + (dy1 - dy0)

    patch  = bgra[sy0:sy1, sx0:sx1]
    alpha  = patch[:, :, 3:4].astype(np.float32) / 255.0
    fg     = patch[:, :, :3].astype(np.float32)
    bg     = base_bgr[dy0:dy1, dx0:dx1].astype(np.float32)

    blended = (fg * alpha + bg * (1.0 - alpha)).astype(np.uint8)
    base_bgr[dy0:dy1, dx0:dx1] = blended
    return base_bgr


def ensure_alpha(img):
    """确保图像有 alpha 通道。"""
    if img.shape[2] == 4:
        return img
    gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, alpha = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY_INV)
    bgra = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    bgra[:, :, 3] = alpha
    return bgra


# ═══════════════════════════════════════════════════════════
#  单手试戴处理
# ═══════════════════════════════════════════════════════════

def process_one_hand(stem, nail_pints, output_dir):
    """
    对单张手部图片执行完整试戴流程。

    Args:
        stem:       图片名（不含扩展名），如 "a13_natural"
        nail_pints: s10 读取的美甲 bottom 点列表（5 个手指）
        output_dir: 输出文件夹 Path 对象

    Returns:
        True/False
    """
    # ── 路径 ──
    hand_path    = Path(HAND_DIR) / f"{stem}.png"
    angle_path   = Path(ANGLE_DIR) / f"{stem}_angle.txt"
    s12_csv_path = Path(S12_DIR) / stem / "extreme_points.csv"

    if not hand_path.exists():
        print(f"  ❌ 手部图片不存在: {hand_path}")
        return False

    if not angle_path.exists():
        print(f"  ❌ 角度文件不存在: {angle_path}")
        return False

    if not s12_csv_path.exists():
        print(f"  ❌ s12 CSV 不存在: {s12_csv_path}")
        return False

    # ── 读取 ──
    hand_img = cv2.imread(str(hand_path))
    if hand_img is None:
        print(f"  ❌ 无法读取手部图片: {hand_path}")
        return False

    angles       = read_finger_angles(str(angle_path))
    mask_extremes = read_mask_extreme_info(str(s12_csv_path))

    print(f"  📐 角度: " + ", ".join([f"{a:.1f}°" for a in angles[:5]]))
    print(f"  📏 对齐点:")
    for i in range(5):
        print(f"    {FINGER_NAMES[i]}: 美甲T_min={nail_pints[i]['pt_min']} → "
              f"手部bottom={mask_extremes[i]['pt_bottom']}")

    h_h, h_w = hand_img.shape[:2]
    print(f"  🖼 手部尺寸: {h_w}x{h_h}")

    debug_img = hand_img.copy()
    records   = []

    # ── 逐个手指试戴 ──
    for i in range(5):
        nail_path    = Path(NAIL_DIR) / f"a2_nail{i+1}_rotated.png"
        nail_bottom  = nail_pints[i]["pt_min"]
        hand_bottom  = mask_extremes[i]["pt_bottom"]

        if not nail_path.exists():
            print(f"    [{FINGER_NAMES[i]}] ⚠ 美甲文件不存在，跳过")
            continue

        # 读取美甲并确保有 alpha
        nail_img = cv2.imread(str(nail_path), cv2.IMREAD_UNCHANGED)
        if nail_img is None:
            print(f"    [{FINGER_NAMES[i]}] ❌ 无法读取美甲")
            continue

        nail_img = ensure_alpha(nail_img)
        nail_h, nail_w = nail_img.shape[:2]

        # 计算粘贴位置：美甲根部对齐手部根部
        paste_x = hand_bottom[0] - nail_bottom[0]
        paste_y = hand_bottom[1] - nail_bottom[1]

        print(f"    [{FINGER_NAMES[i]}] "
              f"nail_bottom={nail_bottom}  hand_bottom={hand_bottom}  "
              f"paste=({paste_x}, {paste_y})")

        # Alpha 合成
        hand_img = alpha_blend_onto(hand_img, nail_img, paste_x, paste_y)

        # 调试标注
        cv2.circle(debug_img, hand_bottom, 6, COLORS[i], -1)
        cv2.circle(debug_img, hand_bottom, 7, (255, 255, 255), 1)
        cv2.putText(debug_img, f"{i+1}",
                    (hand_bottom[0] + 10, hand_bottom[1] + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS[i], 2)

        records.append({
            "finger":     FINGER_NAMES[i],
            "nail_bottom": nail_bottom,
            "hand_bottom": hand_bottom,
            "paste_x":    paste_x,
            "paste_y":    paste_y,
            "nail_size":  f"{nail_w}x{nail_h}",
        })

    # ── 保存 ──
    output_dir.mkdir(parents=True, exist_ok=True)

    tryon_path = output_dir / f"{stem}_tryon.png"
    cv2.imwrite(str(tryon_path), hand_img)
    print(f"    ✅ 试戴结果 → {tryon_path}")

    debug_path = output_dir / f"{stem}_tryon_debug.png"
    cv2.imwrite(str(debug_path), debug_img)
    print(f"    🔍 调试图 → {debug_path}")

    info_path = output_dir / "alignment_info.csv"
    with open(info_path, "w", encoding="utf-8") as f:
        f.write("手指,美甲T_min_x,美甲T_min_y,手部bottom_x,手部bottom_y,"
                "paste_x,paste_y,美甲尺寸\n")
        for r in records:
            f.write(f"{r['finger']},"
                    f"{r['nail_bottom'][0]},{r['nail_bottom'][1]},"
                    f"{r['hand_bottom'][0]},{r['hand_bottom'][1]},"
                    f"{r['paste_x']},{r['paste_y']},"
                    f"{r['nail_size']}\n")
    print(f"    📊 对齐信息 → {info_path}")

    print(f"    ✅ {len(records)}/5 个手指试戴完成")
    return True


def main():
    print("=" * 65)
    print("  s13_tryOnV2 — 美甲试戴根部点对点对齐合成")
    print("=" * 65)

    # ── 读取 s10 美甲 bottom 点（所有手共用同一套美甲） ──
    if not Path(NAIL_PINT_CSV).exists():
        print(f"[FATAL] s10 坐标文件不存在: {NAIL_PINT_CSV}")
        print(f"  请先运行 s10_getbottomPint.py")
        sys.exit(1)

    nail_pints = read_nail_pint_info(NAIL_PINT_CSV)
    print(f"\n✅ s10 美甲 bottom 点已读取 ({len(nail_pints)} 个)")

    # 验证 s9 美甲文件
    print(f"\n验证 s9 旋转后美甲文件:")
    for i in range(5):
        nail_path = Path(NAIL_DIR) / f"a2_nail{i+1}_rotated.png"
        ok = nail_path.exists()
        print(f"  {'✓' if ok else '✗'} {FINGER_NAMES[i]}: {nail_path}")
        if not ok:
            print(f"[FATAL] 美甲文件缺失，请先运行 s9")
            sys.exit(1)

    # ── 扫描 s12 输出文件夹，确定需要处理哪些手 ──
    s12_base = Path(S12_DIR)
    if not s12_base.exists():
        print(f"[FATAL] s12 输出目录不存在: {S12_DIR}")
        sys.exit(1)

    # 找出所有含 extreme_points.csv 的子文件夹
    stems = sorted([
        d.name for d in s12_base.iterdir()
        if d.is_dir() and (d / "extreme_points.csv").exists()
    ])

    if not stems:
        print(f"[WARN] s12 目录下未找到任何 extreme_points.csv")
        print(f"  尝试直接处理 a13_natural...")
        stems = ["a13_natural"]

    print(f"\n找到 {len(stems)} 张手部图片的 s12 结果:")
    for s in stems:
        print(f"  - {s}")

    # ── 逐手处理 ──
    print(f"\n{'='*65}")
    success = 0
    for stem in stems:
        print(f"\n── 试戴: {stem} ──")
        out_dir = Path(OUTPUT_DIR) / stem
        if process_one_hand(stem, nail_pints, out_dir):
            success += 1

    # ── 汇总 ──
    print(f"\n{'='*65}")
    print(f"全部完成! {success}/{len(stems)} 张手部图片试戴成功")
    print(f"输出目录: {os.path.abspath(OUTPUT_DIR)}")
    print("=" * 65)


if __name__ == "__main__":
    main()
