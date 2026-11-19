# DevIntel

**A developer intelligence and tech trend analysis platform.**

DevIntel aggregates public data from GitHub, Stack Overflow, Hacker News, dev.to, npm, PyPI, Hugging Face, and Kaggle. It turns these signals into a transparent, weighted score and growth metric for 87+ technologies, helping developers answer the question: *"What should I learn next?"*

---

## The Problem

Developers trying to figure out what to learn have to check GitHub Trending, Stack Overflow, Hacker News, and job boards separately. Each shows only one slice of the picture, and most only highlight what is *already* popular. DevIntel brings these signals together and highlights what is *growing fastest*.

## Core Features

| Feature | Description |
|---|---|
| **DevIntel Score** | A 0–100 score based on 8 weighted signals (SO questions, GitHub activity, HN demand, Wikipedia views, etc.), using percentile ranks so massive ecosystems don't flatten the curve. |
| **"Taking Off" Flag** | Identifies emerging technologies by requiring cross-source agreement, a minimum growth rate, and a baseline score. |
| **Backtest Engine** | Validates the "Taking Off" flag against historical data (7, 14, or 30-day horizons) to prove its predictive accuracy. |
| **Skill Gap Analyzer** | Connect your GitHub or manually select your stack. DevIntel recommends what to learn next based on market demand and co-occurrence data. |
| **AI & Data Hub** | Dedicated tracking for Hugging Face (trending models/datasets) and Kaggle (hot notebooks/competitions). |
| **Community & Moderation** | Discussion threads on every technology, article, and repo. Includes upvotes, reports, auto-hiding for spam, and a full moderator admin panel. |
| **Live Comparisons** | Side-by-side breakdown of any 2–3 technologies, including score history charts and raw signal comparisons. |

## Architecture

```text
GitHub Actions (daily)          Supabase PostgreSQL          Browser
        |                              ^                       |
        v                              |                       v
  Python collectors  --->  metric_snapshots, articles,   React 19 + Tailwind 4
  (9 sources)              trending_repos, ...                 ^
        |                              ^                       |
        v                              |                       |
  Analysis step  ----------->  tech_scores  ------>  FastAPI (REST API)
```

## Tech Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy, httpx, Authlib, SlowAPI (rate limiting) |
| **Database** | PostgreSQL (Supabase) with Row-Level Security (RLS) enforced |
| **Frontend** | React 19, Vite, Tailwind CSS 4, Three.js (3D interactive hero) |
| **Automation** | GitHub Actions (daily pipeline with isolated testing) |

## Security & Performance

- **Rate Limiting:** All public API endpoints are protected against spam (max 30 requests/min per IP).
- **Row-Level Security (RLS):** Enforced at the database level; the frontend never directly accesses the DB.
- **Server-Side Caching:** Read-heavy endpoints (rankings, feeds) are cached to minimize database load.
- **Zero Leaks:** API documentation (`/docs`) and frontend source maps are strictly disabled in production.

## Getting Started

**Requirements:** Python 3.12+, Node.js 20+, and PostgreSQL (or SQLite for local dev).

```bash
git clone https://github.com/anaydev29/DevIntel.git
cd DevIntel
```

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env         # Then edit .env with your DATABASE_URL and GITHUB_TOKEN
python -m app.seed           # Initialize tables and the technology catalog
python run_pipeline.py       # Run all collectors and analysis
uvicorn app.main:app --reload
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev                  # Runs on http://localhost:5173, proxies API to :8000
```

### 3. Tests

```bash
cd backend
pytest -q                    # Runs against an in-memory SQLite database
```

## Deployment

DevIntel is designed for single-server deployment. A `Dockerfile` is included in the repo root. It installs Python dependencies, builds the React frontend, and serves both via FastAPI.

To deploy on platforms like Render or Railway:

1. Set `ENVIRONMENT=production` in your environment variables.
2. Provide `DATABASE_URL` (use the Supabase Session Pooler), `SESSION_SECRET`, and `PUBLIC_BASE_URL`.
3. The platform will auto-detect the Dockerfile and build the image.

## Roadmap

- [x] Multi-source daily data pipeline with GitHub Actions
- [x] DevIntel Score, 30-day growth, and "Taking Off" emerging flag
- [x] Dashboard: Rankings, Compare, Blogs, News, Trending Repos, AI Hub
- [x] Skill-gap analyzer (GitHub integration + manual selection)
- [x] Google OAuth, user profiles, saved skills, and watchlists
- [x] Community discussions with full moderation tools and audit logs
- [x] Backtest validation for the emerging flag algorithm
- [x] Production hardening: rate limiting, RLS, caching, and disabled debug endpoints
- [ ] Fine-tune "Taking Off" thresholds as 60+ days of historical data accumulates
- [ ] Add Reddit and State of JS survey data sources

## Contributing

Contributions, feedback, and feature requests are welcome. Feel free to open an issue or submit a pull request.

## About

Built by **Anay Shivhare** — [GitHub: @anaydev29](https://github.com/anaydev29)

## License

Released under the [MIT License](LICENSE).