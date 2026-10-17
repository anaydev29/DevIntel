"""Run collectors from the command line (and from GitHub Actions later).

  python run_pipeline.py                    # all technologies
  python run_pipeline.py python react       # only these slugs
"""
import sys

from app.collectors.github import GitHubCollector
from app.database import Base, SessionLocal, engine
from app.seed import seed

if __name__ == "__main__":
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
        run = GitHubCollector().run(db, only_slugs=sys.argv[1:] or None)
        print(f"[{run.source.name}] status={run.status} records={run.records_fetched} errors={run.error_count}")
        if run.error_log:
            print(run.error_log)
