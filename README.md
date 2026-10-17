# DevIntel

**A Unified Tech-Intelligence Aggregation Platform for Developers**

DevIntel aggregates trending GitHub repositories, developer articles, and community
discussions from multiple platforms into a single place — so developers don't have to
check five different sites to know what's happening in tech.

> Status: 🚧 Milestone 1 — Data acquisition layer (scrapers + API connectors)

---

## Problem

Developers currently track technology trends by manually checking GitHub Trending,
Hacker News, Dev.to, and various blogs separately. This is repetitive, time-consuming,
and gives no way to see when a topic is gaining traction across *multiple* sources at once.

## Solution

DevIntel automatically collects data from several developer platforms on a schedule,
normalizes it into a common format, and (in later milestones) ranks and correlates it
to surface genuine trends rather than isolated mentions.

---

## What's in this repo (Milestone 1)

This milestone covers the **data acquisition layer** — the scripts that pull raw data
from each source.

| File | Description |
|---|---|
| `hackernews_scraper.py` | Scrapes post titles, links, score, and comment count from the Hacker News front page using `requests` + `BeautifulSoup`. |
| `devto_scraper.py` | Scrapes article titles, author, tags, and publish date from Dev.to for a given tag. |
| `github_api.py` | Queries the GitHub REST API for trending repositories filtered by language and sorted by stars. |
| `export_utils.py` | Helper functions to export scraped data to CSV/JSON for inspection. |

## Tech Stack

- **Language:** Python 3
- **Scraping:** `requests`, `BeautifulSoup4`
- **APIs:** GitHub REST API, Hacker News API, Dev.to API
- **Planned (next milestones):** FastAPI, PostgreSQL, Celery/Redis, Next.js

## How to run

```bash
# clone the repo
git clone https://github.com/<your-username>/devintel.git
cd devintel

# install dependencies
pip install -r requirements.txt

# run a scraper
python hackernews_scraper.py
python devto_scraper.py
python github_api.py
```

Each script prints extracted records to the console and saves them as CSV/JSON in the
`output/` folder.

## Sample Output

| Source | Fields Extracted |
|---|---|
| Hacker News | title, url, score, comments, rank |
| Dev.to | title, author, tags, published date, reactions |
| GitHub | repo name, owner, description, language, stars, forks, last updated |

## Roadmap

- [x] Milestone 1 — Scrapers & API connectors for GitHub, Hacker News, Dev.to
- [ ] Milestone 2 — PostgreSQL schema + scheduled data collection (Celery/APScheduler)
- [ ] Milestone 3 — FastAPI backend with search, filter, and trending-score endpoints
- [ ] Milestone 4 — Next.js dashboard
- [ ] Milestone 5 — Cross-source topic correlation & trend detection
- [ ] Final — Deployment & documentation

## Author

**Anay Shivhare**
Enrollment No. BTCD25O1017 | Branch: CSD
