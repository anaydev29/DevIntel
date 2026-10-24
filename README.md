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
| **My profile** | Sign in with Google to save your skills (they pre-fill the Skill gap tab), keep a GitHub username, and build a watchlist of technologies. Browsing never needs an account, and you can delete your account at any time. |
| **Discussions** | Every technology, blog post, news item and repository has a discussion: comments, replies, upvotes and a report button. Anyone can read; signing in is needed to write. | 
| **Moderation** | Visible only to moderators and admins: a queue of reported comments (keep, remove or ban the author), an audit log of every decision, and, for admins, a People list to appoint moderators. |
| **Compare** | Pick two technologies (for example FastAPI vs Django) and see a side-by-side summary, every signal with the leader highlighted, and a score-over-time chart. |
| **Blogs** | The most popular dev.to articles of the last two weeks, filterable by technology. |
| **News** | The current Hacker News front page. |
| **Trending repos** | The most-starred GitHub repositories created in the last 7 days, filterable by language. |

A data-freshness strip at the top shows when each source was last collected and whether the run succeeded.

## How the analysis works

Everything is computed from daily snapshots stored in the database. The formulas are documented at the top of [`backend/app/analysis.py`](backend/app/analysis.py).

**DevIntel Score (0 to 100).** Each technology gets a percentile rank among all technologies on seven signals. The score is the weighted average of those ranks. Ranks are used instead of raw counts so that very large numbers (Python) do not flatten everyone else. If a source has no data for a technology, the remaining weights are re-normalized.

| Signal | Weight |
|---|---|
| Stack Overflow questions, last 30 days | 25% |
| Share of Hacker News job posts mentioning it (hiring demand) | 20% |
| GitHub repositories tagged with the topic | 15% |
| Stars on the top 10 repositories | 15% |
| Hacker News stories, last 30 days | 10% |
| Stack Overflow questions, all time | 10% |
| Hacker News points, last 30 days | 5% |

**30-day growth.** The latest value of three signals (GitHub repository count, Stack Overflow questions, Hacker News stories) is compared with the oldest snapshot inside the last 30 days and scaled to a 30-day rate. It needs at least 7 days of history, so it shows "n/a" at first.

**Taking off (emerging flag).** A technology is flagged only if all of these hold:
- its score is at least 20, so tiny projects cannot spike the list
- its 30-day growth is at least 15%
- at least 2 of the 3 growth signals are positive (cross-source agreement)
- its growth is in the top 20% of the eligible technologies

**Explaining and re-weighting the score.** The rank each signal earned is stored for every technology, so the popup can show exactly how a score adds up and the sliders can recompute it in the browser with the same formula. Download counts from npm and PyPI are shown in the popup and in Compare but are deliberately **not** part of the score: they include automated installs and cannot be compared between the two registries. The "Taking off" flag does not change with the sliders.

The thresholds are starting values. The plan is to tune them with a backtest once 30 days of history exist.

## Data sources

| Source | Used for | Access |
|---|---|---|
| GitHub Search API | Repository counts, stars and forks per topic; trending repositories | Token (provided automatically in GitHub Actions) |
| Stack Exchange API | Question counts and new questions in the last 30 days per tag | Optional key (raises the daily quota) |
| Hacker News (Algolia API) | Story mentions and points per technology; the front page; job-post demand from the monthly "Who is hiring?" thread | No key |
| dev.to API | Popular articles per technology tag | No key |
| npm and PyPI download statistics | Weekly downloads for technologies whose main package is the technology itself (React, Vue, Angular, Svelte, Next.js, TypeScript, Tailwind CSS on npm; Django, Flask, FastAPI, PyTorch, TensorFlow, LangChain on PyPI) | No key |

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

`technologies`, `technology_aliases`, `sources`, `metric_snapshots`, `repositories`, `pipeline_runs`, `tech_scores`, `articles`, `trending_repos`, `users`, `user_skills`, `watchlist_items`, `threads`, `comments`, `comment_votes`, `comment_reports`, `user_bans`, `moderation_actions`, `score_components`

## Project structure

```
.github/workflows/daily-pipeline.yml   daily collection (tests, then pipeline)
backend/
  app/
    models.py  database.py  config.py  schemas.py  main.py
    seed.py  normalize.py  analysis.py  skillgap.py  github_profile.py
    collectors/   base, github, stackoverflow, hackernews, hn_hiring, devto, hn_frontpage, trending_repos, downloads
    routers/      meta, technologies, rankings, feed, compare, skills, auth, me, discussions, moderation
  run_pipeline.py        command-line entry point for the collectors and analysis
  tests/                 pytest suite (73 tests, run on in-memory SQLite, no network)
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

To run a single source: `python run_pipeline.py --source devto`. Valid sources are `github`, `stackoverflow`, `hackernews`, `hn_hiring`, `devto`, `hn_frontpage`, `github_trending`, `npm` and `pypi`. You can also limit it to some technologies: `python run_pipeline.py python react`.

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
| `GET /rankings/breakdown` | Every technology's score with the rank it earned on each signal (powers the popup breakdown and the sliders) |
| `GET /rankings/emerging` | Technologies flagged as taking off, fastest growth first |
| `GET /technologies` | List and search (`q`, `category`) |
| `GET /technologies/{name}` | One technology with latest metrics, score and growth (aliases accepted) |
| `GET /technologies/{name}/metrics` | Metric history for charts (`metric`, `days`) |
| `GET /compare?techs=fastapi,django` | Side-by-side data for 2 or 3 technologies |
| `POST /skills/gap` | Skill-gap analysis from `skills` and/or `github_username` (optional `category`) |
| `GET /feed/blogs` | Popular dev.to articles (`tech`, `days`, `limit`) |
| `GET /feed/news` | Hacker News front page |
| `GET /feed/repos` | Trending new repositories (`language`) |
| `GET /auth/google/login`, `/auth/google/callback`, `GET /auth/me`, `POST /auth/logout` | Google sign-in and the login session (`/auth/me` also returns the saved skills and watchlist in one request) |
| `GET/PUT /me/profile`, `PUT /me/skills`, `PUT/DELETE /me/watchlist/{name}`, `DELETE /me` | Saved profile, skills, watchlist and account deletion (sign-in required) |
| `GET /discussions?kind=&ref=`, `GET /discussions/counts` | Read a discussion, or comment counts for a list of items (public) |
| `POST /discussions/comments`, `PUT/DELETE /discussions/comments/{id}`, `PUT .../vote`, `POST .../report` | Write, edit, delete, upvote and report comments (sign-in required) |
| `GET /moderation/queue`, `/moderation/log`, `POST /moderation/comments/{id}/action`, `POST/DELETE /moderation/users/{id}/ban` | Moderator tools (moderators and admins only) |
| `GET /moderation/users`, `PUT /moderation/users/{id}/role` | Appoint moderators (admins only) |
| `GET /categories`, `/pipeline/runs`, `/health` | Metadata, freshness log, health check |

## Performance

When the database is hosted far away, every query is a network round trip, so the main cost of a page is how many queries it makes. The code is tuned for that and guarded by tests (`backend/tests/test_performance.py`):

- **Query budgets:** each endpoint has a maximum number of queries that a test enforces (for example the skill-gap request went from 17 queries to 6).
- **Server cache:** read-only answers (rankings, feeds, compare, technology details) are reused for `CACHE_SECONDS` (default 120; `0` turns it off). A repeat request costs no database round trip. Anything personal (profile, discussions, moderation) is never cached.
- **Indexes** that older databases lack are added at startup.
- **Compression:** API responses are gzip-compressed, and built files in `/assets` are cached by browsers for a year.
- **Frontend:** fonts are bundled (no request to Google), tabs are loaded on demand and prefetched when the browser is idle, and public API answers are reused in the browser for a minute.

The biggest remaining factor is distance: keep the database and the server in the same region, and as close to your users as you can.

## Google login setup (optional)

Without these settings the app works normally and the sign-in button explains that sign-in is not set up.

1. In the Google Cloud Console, create a project. Menu names change, so look for **OAuth consent screen** (now part of "Google Auth Platform").
2. Set the app name, a support email and user type *External*. Request only the basic scopes: `openid`, `email`, `profile`.
3. While the app is in *Testing* status, only the Google accounts you add as **test users** (up to 100) can sign in. Publishing the app lifts that limit, and Google may require verification before showing a custom app name or logo.
4. Create **Credentials**, then **OAuth client ID**, type *Web application*, with this authorized redirect URI for development:
   - `http://localhost:5173/auth/google/callback`

   Add your production URL plus `/auth/google/callback` once deployed. Changes in Google Cloud can take a few minutes to apply.
5. Put the values in `backend/.env`:

```
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
SESSION_SECRET=a-long-random-string      # python -c "import secrets; print(secrets.token_urlsafe(48))"
PUBLIC_BASE_URL=http://localhost:5173    # development: fixes the redirect address
```

Always open the app at `http://localhost:5173` (not `127.0.0.1`) when signing in. The Vite dev server hides the address you opened from the backend, so without `PUBLIC_BASE_URL` Google would see `127.0.0.1:8000` and reject it with `redirect_uri_mismatch`. If you use the single-server build on port 8000 instead, set `PUBLIC_BASE_URL=http://localhost:8000` and register `http://localhost:8000/auth/google/callback`.

In production set `PUBLIC_BASE_URL=https://your-domain` and `COOKIE_SECURE=true`. Never commit these values.

**Privacy:** the app stores only your Google id, email, name and picture, plus the skills, GitHub username and watchlist you choose to save. It never sees your Google password. "Delete my account" removes everything.

## Discussion rules and moderation

Plain text only (nothing a user types is ever run as HTML), 2,000 characters, at most 2 links per comment, 10 comments per hour per user, no identical repeat posts, replies one level deep. Public names are shortened to "First L." and email addresses are never shown to other users.

- **Reports:** a comment reported by 3 different accounts that are more than a day old is hidden automatically. Reports from brand-new accounts are recorded and shown to moderators but do not trigger the hide, so fresh accounts cannot silence people.
- **Moderators** see a queue of reported comments and can keep one (shows it again), remove it, or ban its author. A decision closes the open reports, so a restored comment is not hidden again by old reports.
- **Bans:** a banned user can read but cannot post, edit, vote or report, and can still delete their own comments and account.
- **Audit log:** every restore, removal, ban, unban and role change is recorded with who did it.
- **Roles:** the admin is set only through `ADMIN_EMAILS` in the server settings (a comma-separated list of Google emails; the role is applied the next time that person signs in). Admins appoint moderators from the Moderation tab. Moderators cannot ban other moderators or admins.
- **Pages:** "Community guidelines" and "Privacy" are linked in the footer. Add the project contact email to the privacy page before launch.

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
- **Moderation is manual.** Moderators have to check the queue; there are no notifications yet.
- **Sign-in is limited while the Google app is in testing.** Only listed test users can sign in until the app is published.
- **Hiring signal is approximate.** It counts keyword matches in one month's "Who is hiring?" thread. "Go" is counted only when written "golang", so it is under-counted, and the thread skews toward startups and the US.
- **Bias.** Hacker News skews toward startups and the US, and Stack Overflow question counts favor older technologies. That is why growth is shown next to size everywhere.
- **API limits.** Each source has rate limits, and one failing technology never stops a run. Failures are recorded in `pipeline_runs`.

## Roadmap

- [x] Data pipeline with four sources, daily automation and a data-freshness log
- [x] DevIntel Score, 30-day growth and the emerging flag
- [x] Dashboard: rankings, compare, blogs, news, trending repos
- [x] Skill-gap analyzer (pick skills or enter a GitHub username, see what to learn next)
- [ ] Syllabus gap analyzer (map a course syllabus to current technologies)
- [x] Hiring-demand signal from the monthly "Who is hiring?" threads
- [ ] Technology detail pages with related technologies and learning resources
- [x] Accounts: Google sign-in, profile, saved skills, watchlist
- [x] Discussions on technologies, blogs, news and repos (replies, upvotes, reports)
- [ ] Free topic posts (the data model already supports them; the screen is not built yet)
- [x] Moderation: roles, report queue, bans, audit log, community guidelines and privacy pages
- [ ] Backtest of the emerging flag, then threshold tuning
- [ ] Public deployment with a live link

## About

Built by Anay Shivhare as a Session-Based project (July to December 2026), under the guidance of Prof. Jigyasa Mishra.

License: not yet chosen.
