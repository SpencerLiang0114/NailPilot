"""
s9_rotNail2MatchFingerDirection_v2.py
将提取的美甲图像逆时针旋转，使其方向与对应手指方向对齐。

旋转角度: rotAngle = finger_angle - nail_angle
若 rotAngle < 0, 则 rotAngle += 360 (保证 0~360 度)

使用PIL的rotate(angle, expand=True)保持完整图像内容。

输入:
  E:/meijia/finalCode/s3_nail_Direction/a2_nail1~5.png        # 美甲图像
  E:/meijia/finalCode/s3_nail_Direction/a2_nail1~5_angle.txt   # 美甲角度(每文件一行)
  E:/meijia/finalCode/s7_hands_finger_direction/a13_natural_angle.txt  # 手指方向(5行)

输出:
  E:/meijia/finalCode/s9_rotNail2MatchFingerDirection_v2/a2_nail1~5_rotated.png
"""

import os
import sys
from PIL import Image


# ─── 路径配置 ─────────────────────────────────────────────
NAIL_DIR = r"./s3_nail_Direction"
FINGER_ANGLE_FILE = r"./s7_hands_finger_direction/a13_natural_angle.txt"
OUTPUT_DIR = r"./s9_rotNail2MatchFingerDirection_v2"

FINGER_NAMES = ["thumb", "index", "middle", "ring", "pinky"]


def read_nail_angles(nail_dir):
    """读取每个美甲的旋转角度。
    返回: list[float] — thumb~pinky 的美甲角度
    """
    angles = []
    for i in range(1, 6):
        angle_path = os.path.join(nail_dir, f"a2_nail{i}_angle.txt")
        with open(angle_path, "r") as f:
            line = f.readline().strip()
        angles.append(float(line))
    return angles


def read_finger_angles(finger_path):
    """读取手指自然方向角度。
    返回: list[float] — thumb~pinky 的手指方向角度
    """
    angles = []
    with open(finger_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                angles.append(float(line))
    return angles


def compute_rotation_angles(finger_angles, nail_angles):
    """计算逆时针旋转角度。
    rotAngle = finger_angle - nail_angle
    若 rotAngle < 0, 则 +360
    """
    rot_angles = []
    for fa, na in zip(finger_angles, nail_angles):
        ra = fa - na
        if ra < 0:
            ra += 360.0
        rot_angles.append(ra)
    return rot_angles


def rotate_image(image_path, angle, output_path=None, show=False):
    """
    将图像逆时针旋转指定角度，并保持完整内容（自动扩展画布）。

    参数:
        image_path (str): 输入图像路径
        angle (float): 旋转角度（正值表示逆时针）
        output_path (str): 输出图像路径，若为 None 则自动生成为 "rot_原文件名"
        show (bool): 是否显示旋转后的图像
    """
    # 打开图像
    img = Image.open(image_path)

    # 逆时针旋转，expand=True 使画布包含所有旋转后的内容
    rotated = img.rotate(angle, expand=True)

    # 保存
    if output_path is None:
        base, ext = os.path.splitext(image_path)
        output_path = f"{base}_rot{ext}"

    rotated.save(output_path)

    if show:
        rotated.show()

    return rotated, output_path


def main():
    print("=" * 60)
    print("s9_v2: 美甲旋转 — 匹配手指方向 (使用PIL rotate)")
    print("=" * 60)

    # ── 读取角度 ──
    nail_angles = read_nail_angles(NAIL_DIR)
    finger_angles = read_finger_angles(FINGER_ANGLE_FILE)

    print(f"\n美甲角度: {nail_angles}")
    print(f"手指方向: {finger_angles}")

    # ── 计算旋转角度 ──
    rot_angles = compute_rotation_angles(finger_angles, nail_angles)

    print(f"\n逆时针旋转角度:")
    for name, na, fa, ra in zip(FINGER_NAMES, nail_angles,
                                  finger_angles, rot_angles):
        print(f"  {name:>7}: 美甲{na:7.1f}° → 手指{fa:7.1f}° → 旋转{ra:7.1f}°")

    # ── 创建输出目录 ──
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ── 旋转并保存 ──
    print(f"\n旋转并保存到: {OUTPUT_DIR}")
    for i in range(5):
        img_path = os.path.join(NAIL_DIR, f"a2_nail{i+1}.png")

        if not os.path.exists(img_path):
            print(f"  [错误] 文件不存在: {img_path}")
            continue

        print(f"\n  a2_nail{i+1}.png ({FINGER_NAMES[i]}):")
        print(f"    旋转角度: {rot_angles[i]:.1f}° (逆时针)")

        out_path = os.path.join(OUTPUT_DIR, f"a2_nail{i+1}_rotated.png")
        rotated_img, saved_path = rotate_image(img_path, rot_angles[i], output_path=out_path)

        print(f"    原始尺寸: {rotated_img.size[0]}x{rotated_img.size[1]}")
        print(f"    已保存 → {saved_path}")

    # ── 保存旋转角度到文件 ──
    angle_report = os.path.join(OUTPUT_DIR, "rotation_angles.csv")
    with open(angle_report, "w") as f:
        f.write("手指,美甲角度,手指方向,旋转角度\n")
        for name, na, fa, ra in zip(FINGER_NAMES, nail_angles,
                                      finger_angles, rot_angles):
            f.write(f"{name},{na:.1f},{fa:.1f},{ra:.1f}\n")

    print(f"\n角度报告已保存 → {angle_report}")
    print(f"\n{'=' * 60}")
    print("完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
