"""Run collectors from the command line (and from GitHub Actions later).

  python run_pipeline.py                         # all sources, all technologies
  python run_pipeline.py python react            # all sources, only these slugs
  python run_pipeline.py --source stackoverflow  # one source only
"""
import argparse

from app.analysis import compute_scores
from app.collectors.downloads import NpmDownloadsCollector, PyPIDownloadsCollector
from app.collectors.github import GitHubCollector
from app.collectors.devto import DevToCollector
from app.collectors.hackernews import HackerNewsCollector
from app.collectors.hn_frontpage import HackerNewsFrontPageCollector
from app.collectors.hn_hiring import HackerNewsHiringCollector
from app.collectors.stackoverflow import StackOverflowCollector
from app.collectors.trending_repos import TrendingReposCollector
from app.database import Base, SessionLocal, engine
from app.seed import seed

COLLECTORS = {"github": GitHubCollector, "stackoverflow": StackOverflowCollector,
              "hackernews": HackerNewsCollector, "devto": DevToCollector,
              "hn_frontpage": HackerNewsFrontPageCollector, "github_trending": TrendingReposCollector,
              "hn_hiring": HackerNewsHiringCollector, "npm": NpmDownloadsCollector, "pypi": PyPIDownloadsCollector}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("slugs", nargs="*", help="technology slugs (default: all)")
    parser.add_argument("--source", choices=COLLECTORS, help="run only this source")
    args = parser.parse_args()

    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
        for name, cls in COLLECTORS.items():
            if args.source and args.source != name:
                continue
            run = cls().run(db, only_slugs=args.slugs or None)
            print(f"[{name}] status={run.status} records={run.records_fetched} errors={run.error_count}")
            if run.error_log:
                print(run.error_log)
        print(f"[analysis] {compute_scores(db)}")
