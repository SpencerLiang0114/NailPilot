# NailPilot

NailPilot is a prototype for AI-powered nail try-on and merchant operations. It connects two workflows in one product loop:

- Customers upload a hand photo, choose a nail design, and preview the result before purchase.
- Merchants review nail-art trend signals, ranked styles, and operational suggestions for content, merchandising, and try-on inventory.

The project was built for a Meituan hackathon scenario, but this public repository is structured as a standalone technical report and runnable prototype.

## What It Does

### Customer Try-On

Route: `/user`

- Loads a local catalog of nail products from `backend/nail-tryon-ai/products.json`.
- Lets users upload a hand photo and select a nail-art product.
- Calls the FastAPI backend to generate a virtual try-on image.
- Returns similar product recommendations based on the selected product.
- Uses product IDs as the stable key across catalog, try-on, recommendation, and display logic.

The current public catalog contains 57 nail products.

### Merchant Operations Dashboard

Route: `/ops/manicure-hotspots`

- Accepts trend keywords such as `nail art`, `cat eye nails`, or `press-on nails`.
- Fetches Xiaohongshu/Rnote trend data when API credentials are configured.
- Filters, deduplicates, and scores manicure-related trend items.
- Generates a hotspot report with rankings, trend summaries, and merchant actions.
- Produces suggestions for homepage placement, product ordering, content planning, try-on pool updates, and execution tasks.

If the real trend API is unavailable or unconfigured, the dashboard falls back to a clearly labeled simulated report.

### Entry Page

Route: `/`

The entry page links to the customer try-on flow and the merchant operations dashboard.

## Architecture

```text
Next.js App Router
├── /
│   └── project entry page
├── /user
│   ├── GET  /api/user/initial-products
│   ├── POST /api/user/nail-tryon
│   └── POST /api/user/recommendations
├── /ops/manicure-hotspots
│   └── GET /api/ops/manicure-hotspots
└── FastAPI backend
    ├── GET  /api/initial_products
    ├── POST /api/nail_tryon
    └── POST /recommendations
```

## Tech Stack

- Frontend: Next.js App Router, React, TypeScript, Tailwind CSS
- Backend: FastAPI, Python, local AI try-on pipeline
- Data and ranking: local product catalog, trend-source adapter, manicure relevance filtering, trend scoring, simulated fallback data

## Try-On Model Pipeline

The backend aligns a selected nail-art product image with the user's hand photo and generates a blended virtual try-on result.

1. **Segmentation**
   - Detects the nail-art region in the product image.
   - Detects nail regions in the user's hand photo.
   - Produces masks so the nail-art design can be isolated from its original background.

2. **Hand and nail geometry**
   - Estimates fingertip positions, nail boundaries, finger direction, rotation, and target placement areas.
   - Uses those signals to determine where each nail-art asset should be placed.

3. **Alignment and blending**
   - Rotates, translates, scales, and blends the design into the target nail regions.
   - Preserves the design's texture and color while matching the hand photo's geometry as closely as possible.

## Repository Layout

```text
src/
├── app/
│   ├── page.tsx
│   ├── user/page.tsx
│   ├── merchant/page.tsx
│   ├── ops/manicure-hotspots/page.tsx
│   └── api/
│       ├── user/
│       └── ops/manicure-hotspots/
├── components/
│   └── ops/
├── services/
│   ├── xiaohongshuTrendService.ts
│   ├── manicureTrendFilter.ts
│   ├── manicureTrendScoring.ts
│   ├── manicureReportGenerator.ts
│   └── simulatedManicureReport.ts
└── types/

backend/
└── nail-tryon-ai/
    ├── api.py
    ├── run_pipeline.py
    ├── recommender.py
    ├── products.json
    └── 美甲图74个/
```

## Local Setup

Run the frontend and backend as separate processes.

Default URLs:

```text
Frontend: http://127.0.0.1:3000
Backend:  http://127.0.0.1:8000
```

Main pages:

```text
Entry page:           http://127.0.0.1:3000
Customer try-on:      http://127.0.0.1:3000/user
Operations dashboard: http://127.0.0.1:3000/ops/manicure-hotspots
```

### Frontend

```bash
pnpm install
cp .env.example .env.local
pnpm exec next dev --hostname 127.0.0.1 --port 3000
```

### Backend on macOS

```bash
cd backend/nail-tryon-ai

uv venv
uv pip install -r requirements.txt

export NAIL_TRYON_SAM3_WEIGHTS=/absolute/path/sam3.pt
export NAIL_TRYON_SD_INPAINTING_DIR=/absolute/path/stable-diffusion-inpainting
export NAIL_TRYON_PUBLIC_BASE_URL=http://127.0.0.1:8000

.venv/bin/python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

The backend can also be started with:

```bash
cd backend/nail-tryon-ai
./start_backend.sh
```

### Backend on Windows

Use a simple ASCII path such as `D:\projects\NailPilot`.

```powershell
cd backend\nail-tryon-ai

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:NAIL_TRYON_SAM3_WEIGHTS="D:\models\sam3\sam3.pt"
$env:NAIL_TRYON_SD_INPAINTING_DIR="D:\models\stable-diffusion-inpainting"
$env:NAIL_TRYON_PUBLIC_BASE_URL="http://127.0.0.1:8000"

python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

For NVIDIA GPU setups, install a PyTorch build that matches the local CUDA version and verify availability:

```powershell
python -c "import torch; print(torch.cuda.is_available())"
```

## Configuration

Copy `.env.example` to `.env.local` for frontend and API-route configuration.

Important variables:

```env
NAIL_TRYON_API_BASE_URL=http://127.0.0.1:8000

XHS_API_BASE_URL=https://rnote.dev
XHS_API_TOKEN=
XHS_HOT_SEARCH_ENDPOINT=/api/v2/crawler/creator/hot/inspiration/feed
XHS_KEYWORD_SEARCH_ENDPOINT=/api/v2/crawler/search/notes
XHS_API_AUTH_HEADER=X-API-Key
XHS_API_AUTH_SCHEME=
XHS_API_METHOD=GET
XHS_API_EXTRA_HEADERS=
XHS_HOT_SEARCH_PAGE_SIZE=50
XHS_KEYWORD_SEARCH_PAGE_SIZE=20
```

Backend model paths are configured through shell environment variables and should not be exposed to the browser:

```env
NAIL_TRYON_SAM3_WEIGHTS=/absolute/path/sam3.pt
NAIL_TRYON_SD_INPAINTING_DIR=/absolute/path/stable-diffusion-inpainting
NAIL_TRYON_PUBLIC_BASE_URL=http://127.0.0.1:8000
```

Do not commit:

- `.env.local`
- API keys or access tokens
- model weights
- generated try-on outputs
- private datasets
- temporary cache files

## Data Source Behavior

### Customer Try-On

The try-on flow requires the FastAPI backend and valid local model paths. If the model paths are missing or invalid, the backend returns an error and the frontend should prompt the user to check the backend configuration.

### Operations Report

The operations dashboard supports both real trend data and simulated fallback data. When the real trend API is unavailable, the response remains structurally complete but is marked as simulated:

```json
{
  "dataSource": "simulated",
  "isSimulated": true
}
```

The frontend displays this state clearly so simulated reports are not confused with real trend analysis.

## Verification

Frontend:

```bash
pnpm run lint
pnpm run typecheck
pnpm run build
```

Backend:

```bash
cd backend/nail-tryon-ai
.venv/bin/python -m py_compile api.py run_pipeline.py recommender.py
curl http://127.0.0.1:8000/health
```

## Public Repository Notes

This repository does not include private credentials, private datasets, generated local assets, or model weights. Real try-on generation requires valid local model files referenced by:

```env
NAIL_TRYON_SAM3_WEIGHTS
NAIL_TRYON_SD_INPAINTING_DIR
```

Without a configured Xiaohongshu/Rnote API token, the operations dashboard shows a labeled simulated report.

## Status

Implemented:

- Customer AI nail try-on flow
- FastAPI try-on endpoints
- Local product catalog loading
- Similar-product recommendations
- Merchant hotspot operations dashboard
- Trend report generation
- Simulated fallback reporting
- Entry page linking the main workflows

Possible next steps:

- Connect a stable production trend-data provider.
- Store user try-on preferences with consent.
- Improve matching by hand shape, skin tone, and style intent.
- Connect merchant suggestions to product management, inventory, and publishing systems.
- Add A/B testing and conversion feedback for the merchant dashboard.
