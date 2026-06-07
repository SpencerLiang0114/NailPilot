"""
extractNailBySam3.py
使用 SAM3 模型分割 style 目录下美甲图像中的指甲（nail）。

依赖：ultralytics >= 8.3.237, torch, opencv-python
运行环境：conda activate yolo11

用法：
    python extractNailBySam3.py

输入：E:/meijia/style/*.png
输出：E:/meijia/style_output/
      ├── masks/          # 每张图的二值掩码（白色=指甲区域）
      ├── masked/          # 掩码叠加在原图上的可视化
      ├── crops/           # 每个指甲的裁剪图（带透明背景）
      └── results.json     # 所有结果的汇总
"""

import os
import sys
import json
import argparse
from pathlib import Path

import cv2
import numpy as np
import torch

# ── 路径配置 ──────────────────────────────────────────────
# 可根据实际情况修改

SAM3_WEIGHT = "./sys/sam3_weights/sam3.pt"
BPE_PATH = "./sys/bpe/bpe_simple_vocab_16e6.txt.gz"
IMAGE_DIR     = "./hands"
OUTPUT_DIR    = "./s5_hands_output"

# 文本提示词 —— 告诉 SAM3 要找什么
TEXT_PROMPTS  = ["nail", "fingernail"]

# 置信度阈值（0~1），越高越严格
CONFIDENCE    = 0.25

# 是否使用 FP16 加速（需要 GPU 支持）
USE_HALF      = True

# ──────────────────────────────────────────────────────────


def ensure_dir(path: Path):
    """创建目录（如果不存在）。"""
    path.mkdir(parents=True, exist_ok=True)


def load_predictor():
    """加载 SAM3SemanticPredictor。"""
    from ultralytics.models.sam import SAM3SemanticPredictor

    device = "cuda" if torch.cuda.is_available() else "cpu"
    # CPU 上不能用 half
    use_half = USE_HALF and torch.cuda.is_available()

    overrides = dict(
        conf=CONFIDENCE,
        task="segment",
        mode="predict",
        model=SAM3_WEIGHT,
        half=use_half,
        device=device,
        save=False,          # 我们自己控制保存
        verbose=False,
    )

    print(f"[INFO] 加载 SAM3 模型: {SAM3_WEIGHT}")
    print(f"[INFO] 设备: {device}")
    print(f"[INFO] FP16 加速: {'是' if use_half else '否'}")

    predictor = SAM3SemanticPredictor(overrides=overrides, bpe_path=BPE_PATH)
    return predictor


def process_image(predictor, image_path: Path, out_dirs: dict, prompts: list) -> dict:
    """
    处理单张图片，返回结果字典。

    参数
    ----
    predictor : SAM3SemanticPredictor
    image_path : Path
    out_dirs : dict  包含 'masks', 'masked', 'crops' 三个 Path
    prompts : list    文本提示词列表
    """
    print(f"\n[INFO] 处理: {image_path.name}")

    # 读取原图
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"  [WARN] 无法读取图片，跳过")
        return {"file": image_path.name, "error": "无法读取图片"}

    h, w = img.shape[:2]
    print(f"  尺寸: {w}x{h}")

    # 设置图片（传入 BGR numpy 数组 — SAM3 原生支持）
    try:
        predictor.set_image(img)
    except Exception as e:
        print(f"  [ERROR] set_image 失败: {e}")
        return {"file": image_path.name, "error": str(e)}

    # 用文本提示进行分割
    all_masks = []
    all_boxes = []

    for prompt in prompts:
        try:
            results = predictor(text=[prompt])
        except Exception as e:
            print(f"  [WARN] 提示词 '{prompt}' 推理失败: {e}")
            continue

        if results is None:
            continue

        # results 是一个 Results 对象列表（每个提示词一个）
        for r in results:
            if r.masks is None:
                continue
            # r.masks.data: (N, H, W) 的 tensor
            masks_tensor = r.masks.data
            if masks_tensor is not None and masks_tensor.shape[0] > 0:
                all_masks.append(masks_tensor.cpu())

            # r.boxes 可能包含边界框
            if r.boxes is not None and r.boxes.data is not None:
                boxes_tensor = r.boxes.data  # (N, 6) [x1, y1, x2, y2, conf, cls]
                if boxes_tensor.shape[0] > 0:
                    all_boxes.append(boxes_tensor.cpu())

    # 合并所有 masks
    if not all_masks:
        print(f"  [WARN] 未检测到指甲")
        return {
            "file": image_path.name,
            "nail_count": 0,
            "masks": [],
            "boxes": [],
        }

    # 沿 N 维度拼接
    combined_masks = torch.cat(all_masks, dim=0)  # (total_N, H, W)

    # 去重：对高度重叠的 mask 只保留一个（可选，但有助于清理）
    combined_masks = deduplicate_masks(combined_masks, iou_thresh=0.8)

    nail_count = combined_masks.shape[0]
    print(f"  检测到 {nail_count} 个指甲区域")

    # ── 保存掩码 ──
    # 将每个 mask 缩放到 [0, 255]
    masks_uint8 = (combined_masks.numpy() * 255).astype(np.uint8)  # (N, H, W)

    stem = image_path.stem

    # 1) 综合掩码图（所有指甲区域的并集）
    union_mask = masks_uint8.max(axis=0)  # (H, W)
    mask_path = out_dirs["masks"] / f"{stem}_mask.png"
    cv2.imwrite(str(mask_path), union_mask)
    print(f"  -> 掩码: {mask_path.name}")

    # 2) 掩码叠加可视化
    overlay = img.copy()
    # 用彩色半透明覆盖指甲区域
    color_mask = np.zeros_like(img)
    color_mask[:, :, 0] = 255  # 蓝色通道（OpenCV 是 BGR）
    alpha = 0.4
    # 对于有 mask 的像素
    mask_bool = union_mask > 127
    overlay[mask_bool] = (overlay[mask_bool] * alpha + color_mask[mask_bool] * (1 - alpha)).astype(np.uint8)

    # 画边界框
    if all_boxes:
        for box in torch.cat(all_boxes, dim=0):
            x1, y1, x2, y2 = box[:4].int().tolist()
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 0), 2)

    masked_path = out_dirs["masked"] / f"{stem}_masked.png"
    cv2.imwrite(str(masked_path), overlay)
    print(f"  -> 可视化: {masked_path.name}")

    # 3) 每片指甲裁剪（带透明背景 RGBA）
    nail_infos = []
    for i in range(nail_count):
        mask_i = masks_uint8[i]  # (H, W)
        mask_bool_i = mask_i > 127

        if not mask_bool_i.any():
            continue

        # 找 mask 的边界框
        ys, xs = np.where(mask_bool_i)
        x_min, x_max = xs.min(), xs.max()
        y_min, y_max = ys.min(), ys.max()

        # 稍微扩展裁剪区域
        pad = 5
        x_min = max(0, x_min - pad)
        y_min = max(0, y_min - pad)
        x_max = min(w - 1, x_max + pad)
        y_max = min(h - 1, y_max + pad)

        # 裁剪原图和 mask
        crop_bgr = img[y_min:y_max+1, x_min:x_max+1]
        crop_mask = mask_bool_i[y_min:y_max+1, x_min:x_max+1]

        # 创建 RGBA 图像
        crop_rgba = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2BGRA)
        # 把非指甲区域的 alpha 设为 0
        crop_rgba[:, :, 3] = crop_mask.astype(np.uint8) * 255

        crop_path = out_dirs["crops"] / f"{stem}_nail_{i+1:02d}.png"
        cv2.imwrite(str(crop_path), crop_rgba)

        nail_infos.append({
            "index": i,
            "bbox": [int(x_min), int(y_min), int(x_max), int(y_max)],
            "crop_file": str(crop_path.name),
        })

    print(f"  -> 裁剪: {len(nail_infos)} 个指甲")

    return {
        "file": image_path.name,
        "nail_count": nail_count,
        "mask_file": str(mask_path.name),
        "masked_file": str(masked_path.name),
        "nails": nail_infos,
    }


def deduplicate_masks(masks: torch.Tensor, iou_thresh: float = 0.8) -> torch.Tensor:
    """
    对 mask 进行去重：如果两个 mask 的 IoU > iou_thresh，保留置信度更高的那个。
    如果没有置信度信息，保留面积更大的那个。
    """
    if masks.shape[0] <= 1:
        return masks

    keep = []
    n = masks.shape[0]
    taken = [False] * n

    for i in range(n):
        if taken[i]:
            continue
        for j in range(i + 1, n):
            if taken[j]:
                continue
            iou = compute_mask_iou(masks[i], masks[j])
            if iou > iou_thresh:
                # 保留面积更大的
                area_i = masks[i].sum().item()
                area_j = masks[j].sum().item()
                if area_i >= area_j:
                    taken[j] = True
                else:
                    taken[i] = True
                    break

    keep_indices = [i for i in range(n) if not taken[i]]
    return masks[keep_indices]


def compute_mask_iou(mask_a: torch.Tensor, mask_b: torch.Tensor) -> float:
    """计算两个二值 mask 的 IoU。"""
    # mask 值在 [0, 1] 或 [0, 255] 范围
    a = mask_a > 0.5
    b = mask_b > 0.5
    intersection = (a & b).sum().item()
    union = (a | b).sum().item()
    if union == 0:
        return 0.0
    return intersection / union


def main():
    parser = argparse.ArgumentParser(description="使用 SAM3 分割美甲图像中的指甲")
    parser.add_argument("--conf", type=float, default=CONFIDENCE, help=f"置信度阈值 (默认: {CONFIDENCE})")
    parser.add_argument("--half", action="store_true", default=USE_HALF, help="使用 FP16 加速")
    parser.add_argument("--no-half", action="store_true", help="禁用 FP16")
    parser.add_argument("--image", type=str, default=None, help="只处理指定图片（文件名），不指定则处理全部")
    parser.add_argument("--prompt", type=str, nargs="+", default=TEXT_PROMPTS, help="文本提示词")
    args = parser.parse_args()

    # 配置
    conf = args.conf
    use_half = args.half and not args.no_half
    prompts = args.prompt

    # 检查依赖
    try:
        from ultralytics.models.sam import SAM3SemanticPredictor
    except ImportError:
        print("[ERROR] 未安装 ultralytics，请先安装：")
        print("        pip install -U ultralytics")
        sys.exit(1)

    # 检查文件
    if not os.path.exists(SAM3_WEIGHT):
        print(f"[ERROR] SAM3 权重文件不存在: {SAM3_WEIGHT}")
        sys.exit(1)
    if not os.path.exists(IMAGE_DIR):
        print(f"[ERROR] 图片目录不存在: {IMAGE_DIR}")
        sys.exit(1)

    # 准备输出目录
    out_root = Path(OUTPUT_DIR)
    out_dirs = {
        "masks":  out_root / "masks",
        "masked": out_root / "masked",
        "crops":  out_root / "crops",
    }
    for d in out_dirs.values():
        ensure_dir(d)

    # 获取图片列表
    image_exts = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}
    if args.image:
        image_files = [Path(IMAGE_DIR) / args.image]
    else:
        image_files = sorted([
            f for f in Path(IMAGE_DIR).iterdir()
            if f.suffix.lower() in image_exts and f.is_file()
        ])

    if not image_files:
        print(f"[ERROR] 在 {IMAGE_DIR} 中没有找到图片文件")
        sys.exit(1)

    print(f"[INFO] 找到 {len(image_files)} 张图片")
    print(f"[INFO] 文本提示词: {prompts}")
    print(f"[INFO] 置信度阈值: {conf}")
    print(f"[INFO] 输出目录: {out_root}")

    # 加载模型
    predictor = load_predictor()

    # 处理所有图片
    all_results = []
    success_count = 0

    for img_path in image_files:
        result = process_image(predictor, img_path, out_dirs, prompts)
        all_results.append(result)
        if result.get("nail_count", 0) > 0:
            success_count += 1

    # 保存汇总 JSON
    summary = {
        "total_images": len(image_files),
        "success_images": success_count,
        "total_nails_detected": sum(r.get("nail_count", 0) for r in all_results),
        "prompts_used": prompts,
        "confidence": conf,
        "results": all_results,
    }

    summary_path = out_root / "results.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"[DONE] 处理完成！")
    print(f"  总图片数: {len(image_files)}")
    print(f"  成功分割: {success_count}")
    print(f"  检测指甲总数: {summary['total_nails_detected']}")
    print(f"  结果保存在: {out_root}")
    print(f"  - 掩码:     {out_dirs['masks']}")
    print(f"  - 可视化:   {out_dirs['masked']}")
    print(f"  - 裁剪:     {out_dirs['crops']}")
    print(f"  - 汇总:     {summary_path}")


if __name__ == "__main__":
    main()
