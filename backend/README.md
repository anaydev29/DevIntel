# DevIntel Backend

Developer intelligence and tech trend analysis platform: data pipeline, database, and API.

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # add your GITHUB_TOKEN
docker compose up -d                                   # PostgreSQL on :5432
python -m app.seed                                     # create tables + technology catalog
python run_pipeline.py python react fastapi            # first data pull (3 technologies)
uvicorn app.main:app --reload                          # API docs at http://localhost:8000/docs
pytest                                                 # run tests
```

## Structure
```
app/models.py            database schema (technologies, aliases, metric_snapshots, repositories, pipeline_runs, tech_scores)
app/seed.py              technology catalog + aliases
app/normalize.py         alias -> canonical technology
app/collectors/          base pipeline logic + GitHub collector (add stackoverflow.py, hackernews.py here)
app/routers/             API endpoints
run_pipeline.py          CLI entry point for collection jobs
tests/                   pytest suite (runs on in-memory SQLite)
```

## Endpoints
`GET /health` · `/technologies?q=&category=` · `/technologies/{name}` · `/technologies/{name}/metrics?metric=&days=` · `/categories` · `/pipeline/runs`

## Next
1. Stack Overflow collector  2. Hacker News collector  3. Analysis module (growth, DevIntel Score, emerging flag -> `tech_scores`)  4. Alembic migrations  5. GitHub Actions schedule
