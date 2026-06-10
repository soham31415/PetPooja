# PetPooja PWA

Mobile-first Progressive Web App for the PetPooja social dining backend.

## Stack

- Vite + React 18 + TypeScript
- Tailwind CSS (design tokens mirror the Google Stitch mockups)
- `vite-plugin-pwa` (installable, offline shell, runtime caching)
- `react-router-dom` v6 for routing
- `html5-qrcode` for the in-browser QR scanner
- Native `fetch` + `WebSocket` for the API + live order feed

## Run locally

```bash
# 1. Start the FastAPI backend (from the repo root)
uvicorn app.main:app --reload --port 8000

# 2. Start the PWA (from frontend/)
cd frontend
npm install
cp .env.example .env       # optional, defaults work
npm run dev
```

Open <http://localhost:5173>. The dev server proxies `/api/*` and `/ws/*` to
the backend, so the PWA uses same-origin URLs and ignores CORS.

## Build

```bash
npm run build      # type-check + production build into dist/
npm run preview    # serve the built bundle locally
```

## Routes

| Path                        | Screen                                             |
| --------------------------- | -------------------------------------------------- |
| `/`                         | Onboarding — Scan QR / Sign in / Guest             |
| `/auth`                     | Sign in or create an account                       |
| `/scan`                     | Live QR scanner (with manual code fallback)        |
| `/scan/:qrToken`            | Table confirmation — "Join {N} friends" or "Start" |
| `/sessions/:sessionId/menu` | Menu browsing + group recommendations              |
| `/sessions/:sessionId/cart` | Group cart + live order status                     |
| `/sessions/:sessionId/bill` | Transparent bill split (your share)                |

## Realtime

`useSessionWebSocket` (in `src/session.tsx`) opens
`ws://…/api/v1/sessions/{id}/ws?token=<jwt>` and pushes `order_created`,
`order_status_updated`, `order_item_added`, `order_item_removed` into the
cart and bill screens — so a teammate adding an item or the kitchen
confirming a dish updates everyone's app live.
