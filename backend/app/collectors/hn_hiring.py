"""Hiring-demand collector: counts how many job posts in the latest Hacker News
"Ask HN: Who is hiring?" thread mention each technology (Algolia HN API, no key needed).

Metrics saved per technology:
  hiring.mentions    number of job posts that mention it
  hiring.share_pct   mentions as a percentage of all job posts in the thread (comparable month to month)

Method notes
- Only top-level comments count (each one is one job post); a technology counts once per post.
- A brand-new thread has few posts, so we use the newest thread that has at least MIN_POSTS posts.
- Matching uses explicit, word-boundary patterns. "Go" is only counted when written "golang" (plain "go" is far too
  ambiguous), so Go is under-counted. Swift and Bun are matched case-sensitively for the same reason.
- Hacker News job posts skew toward startups and the US. Treat this as one signal of demand, not the whole market.
"""
import html
import re

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.base import BaseCollector, RateLimitError, save_metric
from app.models import Source, Technology

SEARCH_API = "https://hn.algolia.com/api/v1/search_by_date"
ITEM_API = "https://hn.algolia.com/api/v1/items"
MIN_POSTS = 150

# slug -> (regex, case_sensitive)
PATTERNS: dict[str, tuple[str, bool]] = {
    "python": (r"\bpython\d?\b", False),
    "javascript": (r"\b(?:javascript|ecmascript)\b", False),
    "typescript": (r"\btypescript\b", False),
    "java": (r"\bjava\b", False),
    "go": (r"\bgolang\b", False),
    "rust": (r"\brust\b", False),
    "kotlin": (r"\bkotlin\b", False),
    "swift": (r"\bSwift(?:UI)?\b", True),
    "cpp": (r"(?<![\w+])c\+\+|\bcplusplus\b", False),
    "react": (r"\breact(?:\.?js)?\b", False),
    "vue": (r"\bvue(?:\.?js)?\b", False),
    "angular": (r"\bangular(?:js)?\b", False),
    "svelte": (r"\bsvelte(?:kit)?\b", False),
    "nextjs": (r"\bnext\.?js\b", False),
    "django": (r"\bdjango\b", False),
    "fastapi": (r"\bfast\s?api\b", False),
    "flask": (r"\bflask\b", False),
    "spring-boot": (r"\bspring[\s-]?boot\b", False),
    "nodejs": (r"\bnode\.?js\b", False),
    "deno": (r"\bdeno\b", False),
    "bun": (r"\bBun(?:\.sh)?\b", True),
    "postgresql": (r"\bpostgres(?:ql)?\b", False),
    "mongodb": (r"\bmongo(?:db)?\b", False),
    "redis": (r"\bredis\b", False),
    "sqlite": (r"\bsqlite\b", False),
    "docker": (r"\bdocker\b", False),
    "kubernetes": (r"\bkubernetes\b|\bk8s\b", False),
    "terraform": (r"\bterraform\b", False),
    "pytorch": (r"\bpytorch\b", False),
    "tensorflow": (r"\btensorflow\b", False),
    "langchain": (r"\blangchain\b", False),
    "tailwindcss": (r"\btailwind(?:\s?css)?\b", False),
    "php": (r"\bphp\b", False),
    "ruby": (r"\bruby\b", False),
    "csharp": (r"(?<![\w])c#(?![\w])|\bc sharp\b", False),
    "scala": (r"\bscala\b", False),
    "dart": (r"\bdart\b", False),
    "lua": (r"\blua\b", False),
    "haskell": (r"\bhaskell\b", False),
    "elixir": (r"\belixir\b", False),
    "zig": (r"\bZig\b", True),
    "laravel": (r"\blaravel\b", False),
    "rails": (r"\brails\b", False),
    "aspnet-core": (r"\basp\.net\b", False),
    "express": (r"\bexpress\.?js\b", False),
    "nestjs": (r"\bnest\.?js\b", False),
    "flutter": (r"\bflutter\b", False),
    "react-native": (r"\breact[\s-]native\b", False),
    "jquery": (r"\bjquery\b", False),
    "pandas": (r"\bpandas\b", False),
    "numpy": (r"\bnumpy\b", False),
    "scikit-learn": (r"\bscikit[\s-]learn\b|\bsklearn\b", False),
    "keras": (r"\bkeras\b", False),
    "jupyter": (r"\bjupyter\b", False),
    "huggingface": (r"\bhugging\s?face\b", False),
    "mysql": (r"\bmysql\b", False),
    "mariadb": (r"\bmariadb\b", False),
    "elasticsearch": (r"\belastic\s?search\b", False),
    "cassandra": (r"\bcassandra\b", False),
    "neo4j": (r"\bneo4j\b", False),
    "firebase": (r"\bfirebase\b", False),
    "supabase": (r"\bsupabase\b", False),
    "clickhouse": (r"\bclickhouse\b", False),
    "duckdb": (r"\bduckdb\b", False),
    "kafka": (r"\bkafka\b", False),
    "rabbitmq": (r"\brabbitmq\b", False),
    "git": (r"\bgit\b", False),
    "linux": (r"\blinux\b", False),
    "nginx": (r"\bnginx\b", False),
    "ansible": (r"\bansible\b", False),
    "jenkins": (r"\bjenkins\b", False),
    "prometheus": (r"\bprometheus\b", False),
    "grafana": (r"\bgrafana\b", False),
    "aws": (r"\baws\b|\bamazon web services\b", False),
    "azure": (r"\bazure\b", False),
    "gcp": (r"\bgcp\b|\bgoogle cloud\b", False),
    "graphql": (r"\bgraphql\b", False),
    "grpc": (r"\bgrpc\b", False),
    "webassembly": (r"\bweb\s?assembly\b|\bwasm\b", False),
    "webpack": (r"\bwebpack\b", False),
    "vite": (r"\bvite(?:js)?\b", False),
}
COMPILED = {slug: re.compile(p, 0 if case_sensitive else re.IGNORECASE) for slug, (p, case_sensitive) in PATTERNS.items()}


def clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"https?://\S+", " ", text)  # links often contain company names, not technologies


def count_mentions(posts: list[str]) -> dict[str, int]:
    counts = {slug: 0 for slug in COMPILED}
    for post in posts:
        text = clean(post)
        for slug, pattern in COMPILED.items():
            if pattern.search(text):
                counts[slug] += 1
    return counts


class HackerNewsHiringCollector(BaseCollector):
    source_name = "hn_hiring"
    per_technology = False

    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(timeout=60, headers={"User-Agent": "DevIntel-student-project"})

    def _get(self, url: str, **params) -> dict:
        resp = self.client.get(url, params=params or None)
        if resp.status_code == 429:
            raise RateLimitError("Algolia rate limit")
        resp.raise_for_status()
        return resp.json()

    def _pick_thread_posts(self) -> list[str]:
        hits = self._get(SEARCH_API, tags="story,author_whoishiring", hitsPerPage=10).get("hits", [])
        threads = [h for h in hits if "who is hiring" in (h.get("title") or "").lower()][:2]
        if not threads:
            raise ValueError("no 'Who is hiring?' thread found")
        best: list[str] = []
        for t in threads:  # newest first
            item = self._get(f"{ITEM_API}/{t['objectID']}")
            posts = [c["text"] for c in item.get("children", []) if c.get("text")]
            if len(posts) >= MIN_POSTS:
                return posts
            if len(posts) > len(best):
                best = posts
        return best

    def process(self, db: Session, source: Source, tech: Technology | None) -> int:
        posts = self._pick_thread_posts()
        if not posts:
            raise ValueError("hiring thread has no posts")
        counts = count_mentions(posts)
        saved = 0
        for t in db.scalars(select(Technology)):
            if t.slug in counts:
                save_metric(db, t.id, source.id, "hiring.mentions", counts[t.slug])
                save_metric(db, t.id, source.id, "hiring.share_pct", round(100 * counts[t.slug] / len(posts), 2))
                saved += 2
        return saved
