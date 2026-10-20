# DevIntel

**A developer intelligence and tech trend analysis platform.** DevIntel collects public data from GitHub, Stack Overflow, Hacker News and dev.to every day, turns it into a transparent score and growth signal for each technology, and shows it in a dashboard with rankings, comparisons, blogs, news and trending repositories.

> Academic project (Session-Based, July to December 2026) in the *Web & Internet Applications* category.
> Supports **UN SDG 9: Industry, Innovation and Infrastructure** by making up-to-date technical knowledge easier to reach for students and early-career developers.
>
> **Live demo:** coming soon

---

## The problem

Someone who wants to know "what should I learn?" has to check GitHub Trending, Stack Overflow, Hacker News, blogs and job posts separately. Each shows one slice, none of them combine, and most only show what is *already* popular. DevIntel brings the signals together and also shows what is *growing fastest*.

## Features

| Tab | What it does |
|---|---|
| **Rankings** | 32 technologies ranked by DevIntel Score (0 to 100), with search, category filters, 30-day growth and a "Taking off" panel for fast-growing technologies. Select a row for all the numbers behind it. |
| **Skill gap** | Pick the technologies you know and/or enter a GitHub username. DevIntel reads your public repositories (main language and topics), then ranks what to learn next by demand, momentum and how well each technology fits your stack, with starter articles. |
| **Compare** | Pick two technologies (for example FastAPI vs Django) and see a side-by-side summary, every signal with the leader highlighted, and a score-over-time chart. |
| **Blogs** | The most popular dev.to articles of the last two weeks, filterable by technology. |
| **News** | The current Hacker News front page. |
| **Trending repos** | The most-starred GitHub repositories created in the last 7 days, filterable by language. |

A data-freshness strip at the top shows when each source was last collected and whether the run succeeded.

## How the analysis works

Everything is computed from daily snapshots stored in the database. The formulas are documented at the top of [`backend/app/analysis.py`](backend/app/analysis.py).

**DevIntel Score (0 to 100).** Each technology gets a percentile rank among all technologies on six signals. The score is the weighted average of those ranks. Ranks are used instead of raw counts so that very large numbers (Python) do not flatten everyone else. If a source has no data for a technology, the remaining weights are re-normalized.

| Signal | Weight |
|---|---|
| Stack Overflow questions, last 30 days | 30% |
| GitHub repositories tagged with the topic | 20% |
| Stars on the top 10 repositories | 15% |
| Hacker News stories, last 30 days | 15% |
| Stack Overflow questions, all time | 10% |
| Hacker News points, last 30 days | 10% |

**30-day growth.** The latest value of three signals (GitHub repository count, Stack Overflow questions, Hacker News stories) is compared with the oldest snapshot inside the last 30 days and scaled to a 30-day rate. It needs at least 7 days of history, so it shows "n/a" at first.

**Taking off (emerging flag).** A technology is flagged only if all of these hold:
- its score is at least 20, so tiny projects cannot spike the list
- its 30-day growth is at least 15%
- at least 2 of the 3 growth signals are positive (cross-source agreement)
- its growth is in the top 20% of the eligible technologies

The thresholds are starting values. The plan is to tune them with a backtest once 30 days of history exist.

## Data sources

| Source | Used for | Access |
|---|---|---|
| GitHub Search API | Repository counts, stars and forks per topic; trending repositories | Token (provided automatically in GitHub Actions) |
| Stack Exchange API | Question counts and new questions in the last 30 days per tag | Optional key (raises the daily quota) |
| Hacker News (Algolia API) | Story mentions and points per technology; the front page | No key |
| dev.to API | Popular articles per technology tag | No key |

Only official public APIs are used, with rate-limit handling and a log of every run.

## Architecture

```
GitHub Actions (daily)          Supabase PostgreSQL          Browser
        |                              ^                       |
        v                              |                       v
  Python collectors  --->  metric_snapshots, articles,   React + Tailwind
  (7 sources)              trending_repos, ...                 ^
        |                              ^                       |
        v                              |                       |
  Analysis step  ----------->  tech_scores  ------>  FastAPI (REST API)
```

- **Collectors** fetch data, clean and normalize technology names through an alias table (`reactjs` and `React.js` both become `react`), and store dated snapshots. Re-running a collector on the same day updates rows instead of duplicating them.
- **Analysis** reads the snapshots and writes the Score, growth and emerging flag into `tech_scores`, so the dashboard reads pre-computed rows.
- **API and frontend** are served together: FastAPI serves the built React app at `/` and the REST API alongside it.

### Tech stack

- **Backend:** Python, FastAPI, SQLAlchemy, httpx, pytest
- **Database:** PostgreSQL (Supabase) in production, SQLite or PostgreSQL locally
- **Frontend:** React 19, Vite, Tailwind CSS 4 (neo-brutalist design)
- **Automation:** GitHub Actions (runs the tests, then the full pipeline, every day)

### Database tables

`technologies`, `technology_aliases`, `sources`, `metric_snapshots`, `repositories`, `pipeline_runs`, `tech_scores`, `articles`, `trending_repos`

## Project structure

```
.github/workflows/daily-pipeline.yml   daily collection (tests, then pipeline)
backend/
  app/
    models.py  database.py  config.py  schemas.py  main.py
    seed.py  normalize.py  analysis.py  skillgap.py  github_profile.py
    collectors/   base, github, stackoverflow, hackernews, devto, hn_frontpage, trending_repos
    routers/      meta, technologies, rankings, feed, compare, skills
  run_pipeline.py        command-line entry point for the collectors and analysis
  tests/                 pytest suite (30 tests, run on in-memory SQLite, no network)
frontend/
  src/App.jsx  src/components/  src/lib/
```

## Getting started

**Requirements:** Python 3.12 or newer, Node.js 20.19 or newer, and a PostgreSQL database (or use SQLite for a quick start).

### 1. Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env              # macOS/Linux: cp .env.example .env
```

Edit `.env`:

```
DATABASE_URL=sqlite:///./devintel.db
GITHUB_TOKEN=your_github_token
STACKEXCHANGE_KEY=
```

- `DATABASE_URL` can also be a PostgreSQL URL. `docker compose up -d` starts a local PostgreSQL that matches the default.
- `GITHUB_TOKEN` needs no scopes. Create one at github.com/settings/tokens.
- `STACKEXCHANGE_KEY` is optional.
- Never commit `.env`.

Create the tables, collect data and start the API:

```powershell
python -m app.seed                    # tables + the 32-technology catalog
python run_pipeline.py                # all sources, then the analysis (takes a few minutes)
uvicorn app.main:app --reload --reload-dir app
```

To run a single source: `python run_pipeline.py --source devto`. Valid sources are `github`, `stackoverflow`, `hackernews`, `devto`, `hn_frontpage` and `github_trending`. You can also limit it to some technologies: `python run_pipeline.py python react`.

Interactive API docs are at http://127.0.0.1:8000/docs.

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev                           # http://localhost:5173 (proxies API calls to port 8000)
```

Keep the backend running in a second terminal. For a single-server build, run `npm run build`. FastAPI then serves `frontend/dist` at `/`.

### 3. Tests

```powershell
cd backend
pytest -q
```

## API

| Endpoint | Description |
|---|---|
| `GET /rankings/trending` | Technologies ranked by DevIntel Score (optional `category`, `limit`) |
| `GET /rankings/emerging` | Technologies flagged as taking off, fastest growth first |
| `GET /technologies` | List and search (`q`, `category`) |
| `GET /technologies/{name}` | One technology with latest metrics, score and growth (aliases accepted) |
| `GET /technologies/{name}/metrics` | Metric history for charts (`metric`, `days`) |
| `GET /compare?techs=fastapi,django` | Side-by-side data for 2 or 3 technologies |
| `POST /skills/gap` | Skill-gap analysis from `skills` and/or `github_username` (optional `category`) |
| `GET /feed/blogs` | Popular dev.to articles (`tech`, `days`, `limit`) |
| `GET /feed/news` | Hacker News front page |
| `GET /feed/repos` | Trending new repositories (`language`) |
| `GET /categories`, `/pipeline/runs`, `/health` | Metadata, freshness log, health check |

## Daily automation

`.github/workflows/daily-pipeline.yml` runs every day at 02:30 UTC (08:00 IST) and can also be started by hand from the Actions tab. It installs dependencies, runs the tests, then runs the whole pipeline against the production database.

Setup notes:
- Add a repository secret named `DATABASE_URL` (Settings, Secrets and variables, Actions). It must be the plain URL only, starting with `postgresql://`.
- **Supabase:** use the **Session pooler** connection string, not the direct one. The direct connection is IPv6-only and GitHub Actions runners cannot reach it.
- If the password contains characters such as `@`, `/` or `#`, URL-encode them or use a password with letters and numbers only.
- The workflow is pinned to `ubuntu-24.04` so a change to the `ubuntu-latest` label cannot break it.

## Known limitations

- **Growth needs history.** Growth and the "Taking off" flag only appear after about 7 days of daily collection, and the thresholds can only be tuned properly after about 30 days.
- **GitHub has no official trending API.** "Trending repos" are the most-starred repositories created in the last 7 days, which is an approximation of GitHub's own page.
- **Skill detection is shallow.** GitHub detection uses each repository's main language and topics only, so it misses libraries that are not listed as topics. Picking skills by hand fills the gap.
- **Name ambiguity.** Words like "Go" and "Swift" are ambiguous in Hacker News titles. Overrides reduce the noise, but some remains.
- **Bias.** Hacker News skews toward startups and the US, and Stack Overflow question counts favor older technologies. That is why growth is shown next to size everywhere.
- **API limits.** Each source has rate limits, and one failing technology never stops a run. Failures are recorded in `pipeline_runs`.

## Roadmap

- [x] Data pipeline with four sources, daily automation and a data-freshness log
- [x] DevIntel Score, 30-day growth and the emerging flag
- [x] Dashboard: rankings, compare, blogs, news, trending repos
- [x] Skill-gap analyzer (pick skills or enter a GitHub username, see what to learn next)
- [ ] Syllabus gap analyzer (map a course syllabus to current technologies)
- [ ] Hiring-demand signal from the monthly "Who is hiring?" threads
- [ ] Technology detail pages with related technologies and learning resources
- [ ] Per-item discussion threads
- [ ] Backtest of the emerging flag, then threshold tuning
- [ ] Public deployment with a live link

## About

Built by Anay Shivhare as a Session-Based project (July to December 2026), under the guidance of Prof. Jigyasa Mishra.

License: not yet chosen.
