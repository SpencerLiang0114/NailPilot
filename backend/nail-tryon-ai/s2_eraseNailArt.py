"""
eraseNailArt.py  — 擦除美甲，恢复自然素手
使用 SD Inpainting 将 style 中美甲区域重绘为自然裸甲。

原理：
  1. 复用第一次任务的 SAM3 掩码（style_output/masks/）
  2. SD Inpainting 在掩码白色区域内生成自然指甲
  3. 羽化融合回原图

运行：python s2_eraseNailArt.py
"""

import os, sys, cv2, numpy as np, torch
from pathlib import Path
from PIL import Image

# HuggingFace 国内镜像
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# ── 路径 ──────────────────────────────────────────────────
STYLE_DIR    = "./style"
MASK_DIR     = "./s1_style_output/masks"
SD_MODEL_DIR = "./sys/sd_models/AI-ModelScope/stable-diffusion-inpainting"
OUTPUT_DIR   = "./s2_style_natural"

# ── SD 参数 ───────────────────────────────────────────────
DEVICE       = "cuda" if torch.cuda.is_available() else "cpu"
SD_STEPS     = 25   # GPU 上可以更多步
SD_GUIDANCE  = 7.5
SD_STRENGTH  = 0.90   # 高重绘强度，彻底擦除美甲


def load_pipe():
    """加载 SD Inpainting。"""
    from diffusers import StableDiffusionInpaintPipeline
    dt = torch.float16 if DEVICE == "cuda" else torch.float32
    pipe = StableDiffusionInpaintPipeline.from_pretrained(
        SD_MODEL_DIR, torch_dtype=dt, safety_checker=None,
        requires_safety_checker=False, local_files_only=True)
    pipe = pipe.to(DEVICE)
    print(f"[SD] Inpainting 就绪 ({DEVICE})")
    return pipe


def erase_one(pipe, img_path, mask_path, out_path):
    """擦除单张图的美甲。"""
    img = cv2.imread(str(img_path))
    mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    if img is None or mask is None:
        print(f"  [SKIP] 无法读取 {img_path.name}")
        return

    # mask 膨胀一点确保覆盖完整美甲
    kernel = np.ones((5,5), np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=1)
    mask = (mask > 127).astype(np.uint8) * 255

    h, w = img.shape[:2]

    # 缩小到 512px 边长加速（SD 1.5 原生分辨率即可）
    max_side = 512
    scale = max_side / max(h, w) if max(h, w) > max_side else 1.0
    sh, sw = int(h * scale), int(w * scale)
    sh = max(64, ((sh + 63) // 64) * 64)
    sw = max(64, ((sw + 63) // 64) * 64)

    img_rs = cv2.resize(img, (sw, sh))
    mask_rs = cv2.resize(mask, (sw, sh))

    init = Image.fromarray(cv2.cvtColor(img_rs, cv2.COLOR_BGR2RGB))
    mimg = Image.fromarray(mask_rs)

    print(f"  Erasing ({sw}x{sh})...")
    with torch.no_grad():
        output = pipe(
            prompt="natural bare fingernail, clean nail, nude nail, realistic human hand, skin tone",
            negative_prompt="nail art, polish, color, painted, manicure, design, glitter, decoration",
            image=init, mask_image=mimg,
            num_inference_steps=SD_STEPS, guidance_scale=SD_GUIDANCE,
            strength=SD_STRENGTH, height=sh, width=sw,
        )
    result = output.images[0]
    result_bgr = cv2.cvtColor(np.array(result), cv2.COLOR_RGB2BGR)

    if result_bgr.shape[:2] != (h, w):
        result_bgr = cv2.resize(result_bgr, (w, h))

    # 只在 mask 区域用结果，其余保持原图（二次保障）
    mask_3 = np.repeat((mask > 0)[:,:,np.newaxis], 3, axis=2)
    final = img.copy()
    final[mask_3[:,:,0]] = result_bgr[mask_3[:,:,0]]

    cv2.imwrite(str(out_path), final)
    print(f"  -> {out_path.name}")


def main():
    print("=" * 56)
    print("  擦除美甲 — SD Inpainting 恢复自然裸甲")
    print("=" * 56)

    style = Path(STYLE_DIR)
    mask_dir = Path(MASK_DIR)
    out_dir = Path(OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 加载模型
    print("\n[1/2] 加载 SD Inpainting...")
    pipe = load_pipe()

    # 遍历 style 图片
    images = sorted([f for f in style.iterdir() if f.suffix.lower() in {".png",".jpg",".jpeg"}])
    print(f"\n[2/2] 处理 {len(images)} 张图...")

    count = 0
    for img_path in images:
        stem = img_path.stem
        mask_path = mask_dir / f"{stem}_mask.png"

        if not mask_path.exists():
            print(f"  [SKIP] {img_path.name} — 无掩码")
            continue

        out_path = out_dir / f"{stem}_natural.png"
        if out_path.exists():
            print(f"  [SKIP] {img_path.name} — 已存在")
            count += 1
            continue
        print(f"\n[{count+1}] {img_path.name}")
        try:
            erase_one(pipe, img_path, mask_path, out_path)
            count += 1
        except Exception as e:
            print(f"  [ERROR] {e}")

    print(f"\n{'='*56}")
    print(f"[DONE] {count}/{len(images)} 张完成 → {out_dir}")


if __name__ == "__main__":
    main()
