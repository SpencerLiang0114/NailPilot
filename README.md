# Nail Try-On AI Merchant Ops

Merchant-side dashboard for the Meituan hackathon project **AI Manicure Try-On and Smart Operations**.

This app focuses on the operations side: it reviews manicure hotspots, generates a daily operations report, and recommends merchandising adjustments for nail salons and press-on nail merchants.

## Features

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
- Rnote Xiaohongshu data API

## Getting Started

Install dependencies:

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

Run the development server:

```bash
pnpm exec next dev --hostname 127.0.0.1 --port 3000
```

Open:

```text
http://127.0.0.1:3000/ops/manicure-hotspots
```

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
XHS_HOT_SEARCH_PAGE_SIZE=50
```

Do not commit `.env.local`. API keys must stay server-side.

## Data Behavior

The report generation flow is:

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

## Important Notes

- The dashboard does not auto-generate reports on page load.
- Reports are generated only after the merchant clicks the button.
- Simulated reports are only used when real API data cannot be fetched.
- The UI clearly labels simulated reports to avoid confusing them with real market signals.
