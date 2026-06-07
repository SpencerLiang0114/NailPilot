import json
import mimetypes
import os
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from recommender import recommend_products
from run_pipeline import PipelineConfigurationError, run_nail_tryon_pipeline


BASE_DIR = Path(__file__).resolve().parent
PRODUCTS_PATH = BASE_DIR / "products.json"
LOCAL_IMAGE_DIR = BASE_DIR / "美甲图74个"
STATIC_IMAGE_PREFIX = "/static/images/"
DEFAULT_PUBLIC_BASE_URL = os.getenv("NAIL_TRYON_PUBLIC_BASE_URL", "http://127.0.0.1:8000")

app = FastAPI(title="AI Nail Try-On Backend")
tryon_lock = threading.Lock()

if LOCAL_IMAGE_DIR.exists():
    app.mount(
        STATIC_IMAGE_PREFIX.rstrip("/"),
        StaticFiles(directory=str(LOCAL_IMAGE_DIR)),
        name="nail-images",
    )


def load_products() -> list[dict[str, Any]]:
    with PRODUCTS_PATH.open("r", encoding="utf-8") as f:
        raw_products = json.load(f)

    normalized_products = []
    for product in raw_products:
        item = dict(product)
        if not item.get("image"):
            item["image"] = f"{STATIC_IMAGE_PREFIX}{item['id']}.jpg"
        item["image"] = normalize_image_url(item["image"])
        normalized_products.append(item)
    return normalized_products


def normalize_image_url(image: str) -> str:
    if image.startswith("http://") or image.startswith("https://"):
        return image
    if image.startswith("/"):
        return urljoin(DEFAULT_PUBLIC_BASE_URL.rstrip("/") + "/", image.lstrip("/"))
    return urljoin(DEFAULT_PUBLIC_BASE_URL.rstrip("/") + "/", image)


def resolve_product_image(product: dict[str, Any]) -> str:
    image = str(product.get("image", ""))
    local_candidate = LOCAL_IMAGE_DIR / f"{product['id']}.jpg"
    if image.startswith(DEFAULT_PUBLIC_BASE_URL) and "/static/images/" in image and local_candidate.exists():
        return str(local_candidate)
    if image.startswith("/static/images/") and local_candidate.exists():
        return str(local_candidate)
    if image.startswith("http://") or image.startswith("https://"):
        return image

    raise HTTPException(status_code=404, detail=f"Product image not found for {product['id']}")


def find_product(product_id: str) -> dict[str, Any]:
    for product in products:
        if str(product["id"]).strip() == str(product_id).strip():
            return product
    raise HTTPException(status_code=404, detail="Product not found")


def model_status() -> dict[str, Any]:
    sam3_weights = os.getenv("NAIL_TRYON_SAM3_WEIGHTS", "")
    sd_inpainting_dir = os.getenv("NAIL_TRYON_SD_INPAINTING_DIR", "")
    return {
        "sam3_weights": {
            "configured": bool(sam3_weights),
            "exists": bool(sam3_weights and Path(sam3_weights).exists()),
        },
        "sd_inpainting_dir": {
            "configured": bool(sd_inpainting_dir),
            "exists": bool(sd_inpainting_dir and Path(sd_inpainting_dir).exists()),
        },
    }


products = load_products()
print("商品数量：", len(products))


class RecommendationRequest(BaseModel):
    current_product_id: str
    top_k: int = 8


@app.get("/")
def home():
    return {
        "success": True,
        "service": "AI Nail Try-On Backend",
        "product_count": len(products),
    }


@app.get("/health")
def health():
    return {
        "success": True,
        "product_count": len(products),
        "model_status": model_status(),
    }


@app.get("/api/initial_products")
def initial_products():
    return {"success": True, "count": len(products), "products": products}


@app.get("/products")
def get_products():
    return {"success": True, "count": len(products), "products": products}


@app.post("/recommendations")
async def recommendations(data: RecommendationRequest):
    print("收到推荐请求：", data.current_product_id)
    try:
        recs = recommend_products(
            current_product_id=data.current_product_id,
            products=products,
            top_k=data.top_k,
        )
        return {"success": True, "recommendations": recs}
    except Exception as e:
        print("推荐错误：", str(e))
        return JSONResponse(status_code=400, content={"success": False, "error": str(e)})


@app.post("/api/nail_tryon")
async def nail_tryon(
    product_id: str = Form(...),
    hand_file: UploadFile = File(...),
):
    product = find_product(product_id)
    selected_nail_path = resolve_product_image(product)

    suffix = Path(hand_file.filename or "").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        suffix = ".png"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(hand_file.file, tmp)
        uploaded_hand_path = tmp.name

    try:
        with tryon_lock:
            result_path = run_nail_tryon_pipeline(selected_nail_path, uploaded_hand_path)
    except PipelineConfigurationError as e:
        return JSONResponse(status_code=503, content={"success": False, "error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
    finally:
        Path(uploaded_hand_path).unlink(missing_ok=True)

    if not result_path:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Nail try-on pipeline did not produce a result image."},
        )

    result = Path(result_path)
    media_type = mimetypes.guess_type(result.name)[0] or "image/png"
    return FileResponse(path=str(result), media_type=media_type, filename=result.name)
