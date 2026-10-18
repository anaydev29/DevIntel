# DevIntel Frontend (React + Tailwind + Vite)

Needs Node.js 20.19 or newer (check with `node --version`).

## Develop
```bash
# terminal 1: backend API
cd backend && python -m uvicorn app.main:app --reload --reload-dir app

# terminal 2: frontend (hot reload, proxies API calls to :8000)
cd frontend
npm install
npm run dev          # open http://localhost:5173
```

## Production build
```bash
cd frontend && npm run build     # creates frontend/dist
```
When `frontend/dist` exists, FastAPI serves it at `/`, so one server runs both the API and the dashboard.

## Structure
```
src/App.jsx                     loads data, holds the selected technology
src/components/Hero.jsx         title and data-freshness stickers
src/components/RankingCard.jsx  search, category filter, ranked list
src/components/EmergingCard.jsx the "Taking off" panel
src/components/DetailDialog.jsx popup with all numbers for one technology
src/lib/api.js                  API calls    src/lib/format.js  number/label helpers
src/index.css                   Tailwind + neo-brutalist theme tokens (colors, shadows, fonts)
```
