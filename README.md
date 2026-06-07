# Nail Try-On AI

Meituan hackathon project for **AI Manicure Try-On and Smart Operations**.

The repo now contains both user-side virtual nail try-on and merchant-side intelligent operations:

- `/user`: consumer-facing AI nail try-on flow with a 74-style carousel, hand-photo upload, real FastAPI try-on backend proxy, and 8-style personalized recommendations.
- `/merchant`: merchant entry route, redirected to the manicure hotspot operations dashboard.
- `/ops/manicure-hotspots`: merchant-side trend review, daily report, and execution suggestions.

## Features

- **User AI try-on**: select one of 74 nail styles, upload a hand photo, and request real try-on generation from the FastAPI backend.
- **Personalized recommendations**: after try-on, replace the same carousel with 8 recommended nail styles based on the selected product ID.
- **美甲热点 Review**: manually generate a manicure trend report from the dashboard.
- **Trend chart**: visualizes the top manicure hotspot scores in a pink-purple pearl report card.
- **Daily operations report**: summarizes current hot styles, content direction, pricing suggestions, and inventory checks.
- **Smart execution suggestions**: recommends homepage slots, AI try-on style updates, product list ordering, and merchant todo items.
- **Real API first**: uses Rnote/Xiaohongshu API data when available.
- **Clearly marked simulation fallback**: if the API is unavailable, out of quota, or misconfigured, the app returns a simulated report and labels it as simulated in both data and UI.

## Tech Stack

- Next.js App Router
- React
- TypeScript
- CSS glassmorphism UI
- FastAPI user-side try-on backend
- Python AI try-on pipeline
- Rnote Xiaohongshu data API

## Getting Started

### Frontend

```bash
pnpm install
```

Create a local environment file:

```bash
cp .env.example .env.local
```

Set your Rnote API key in `.env.local`:

```env
XHS_API_TOKEN=your_rnote_api_key
```

Run the Next.js development server:

```bash
pnpm exec next dev --hostname 127.0.0.1 --port 3000
```

Open the portal:

```text
http://127.0.0.1:3000
```

Merchant operations dashboard:

```text
http://127.0.0.1:3000/ops/manicure-hotspots
```

User-side AI try-on page:

```text
http://127.0.0.1:3000/user
```

### User Try-On Backend

The `/user` page talks to the FastAPI backend through the Next.js proxy routes under `/api/user/*`.

Run the user-side FastAPI backend from this repository:

```bash
cd backend/nail-tryon-ai
uv venv
uv pip install -r requirements.txt
export NAIL_TRYON_SAM3_WEIGHTS=/absolute/path/sam3.pt
export NAIL_TRYON_SD_INPAINTING_DIR=/absolute/path/stable-diffusion-inpainting
.venv/bin/python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

Do not run bare `uvicorn api:app` from an Anaconda/base shell; it can use the wrong Python environment and fail with `ModuleNotFoundError: No module named 'fastapi'`. You can also use:

```bash
cd backend/nail-tryon-ai
./start_backend.sh
```

The backend exposes:

- `GET /health`
- `GET /api/initial_products`
- `POST /api/nail_tryon`
- `POST /recommendations`

The Next.js user APIs proxy to `http://127.0.0.1:8000` by default. Override with `NAIL_TRYON_API_BASE_URL` in `.env.local` if the backend runs elsewhere.

## Environment Variables

The default Rnote integration is configured in `.env.example`.

```env
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

User-side try-on environment variables:

```env
# Next.js proxy target, optional. Defaults to http://127.0.0.1:8000.
NAIL_TRYON_API_BASE_URL=http://127.0.0.1:8000

# FastAPI backend model paths. These are shell exports for the backend process,
# not values that should be exposed to the browser.
NAIL_TRYON_SAM3_WEIGHTS=/absolute/path/sam3.pt
NAIL_TRYON_SD_INPAINTING_DIR=/absolute/path/stable-diffusion-inpainting
NAIL_TRYON_PUBLIC_BASE_URL=http://127.0.0.1:8000
```

Do not commit `.env.local`. API keys must stay server-side.

## Data Behavior

### User Try-On Flow

1. The user opens `/user`.
2. The frontend loads 74 nail products from `GET /api/user/initial-products`.
3. The user selects a product ID and uploads a hand photo.
4. The frontend posts multipart form data to `POST /api/user/nail-tryon`.
5. Next.js proxies the request to FastAPI `POST /api/nail_tryon`.
6. FastAPI runs the real Python try-on pipeline and returns the generated image.
7. The frontend calls `POST /api/user/recommendations`.
8. The same carousel is replaced with 8 recommended nail products.

The user backend product source is:

```text
backend/nail-tryon-ai/products.json
```

Local nail images are served from:

```text
backend/nail-tryon-ai/美甲图74个
```

### Merchant Hotspot Flow

The merchant report generation flow is:

1. User clicks **生成报告**.
2. Backend calls the Rnote/Xiaohongshu endpoints.
3. Returned records are normalized into manicure trend items.
4. The system filters manicure-related content.
5. Hotspot scores and merchant actions are generated.
6. If the real API fails, the backend returns a simulated report marked with:

```json
{
  "dataSource": "simulated",
  "isSimulated": true
}
```

When the API works again, the same page automatically returns to real Xiaohongshu data.

## Scripts

```bash
pnpm run lint
pnpm run typecheck
pnpm run build
```

Backend smoke checks:

```bash
cd backend/nail-tryon-ai
.venv/bin/python -m py_compile api.py run_pipeline.py recommender.py
curl http://127.0.0.1:8000/health
```

## Important Notes

- The user try-on backend depends on external model assets and will not run real try-on until `NAIL_TRYON_SAM3_WEIGHTS` and `NAIL_TRYON_SD_INPAINTING_DIR` point to valid local files.
- The user-side carousel must keep product IDs as the integration key; do not use only image URLs or names for recommendation calls.
- The merchant dashboard does not auto-generate reports on page load.
- Merchant reports are generated only after the merchant clicks the button.
- Simulated reports are only used when real API data cannot be fetched.
- The UI clearly labels simulated reports to avoid confusing them with real market signals.
