"""Wikipedia page views: a measure of general public interest in a technology (official Wikimedia API, no key).

Metric saved per technology: wikipedia.views_30d, the human page views of the English article over the last 30 full days.

Notes
- Views reflect curiosity (students, news, school courses), not usage. Linux and Git get many views because
  everyone looks them up, which is why this is one signal among many, ranked against the other technologies.
- A technology without a confident article title is simply skipped. A title that turns out not to exist is
  skipped with a warning in the log instead of failing the whole run.
"""
import logging
import time
from datetime import date, timedelta
from urllib.parse import quote

import httpx
from sqlalchemy.orm import Session

from app.collectors.base import BaseCollector, RateLimitError, save_metric
from app.models import Source, Technology

log = logging.getLogger(__name__)
API = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user"
# Wikimedia asks API users to identify themselves in the User-Agent
USER_AGENT = "DevIntel-student-project (https://github.com/anaydev29/DevIntel)"

WIKI_TITLES = {
    "python": "Python_(programming_language)", "javascript": "JavaScript", "typescript": "TypeScript",
    "java": "Java_(programming_language)", "go": "Go_(programming_language)", "rust": "Rust_(programming_language)",
    "kotlin": "Kotlin", "swift": "Swift_(programming_language)", "cpp": "C++", "react": "React_(software)",
    "vue": "Vue.js", "angular": "Angular_(web_framework)", "svelte": "Svelte", "nextjs": "Next.js",
    "django": "Django_(web_framework)", "fastapi": "FastAPI", "flask": "Flask_(web_framework)",
    "spring-boot": "Spring_Framework", "nodejs": "Node.js", "deno": "Deno_(software)", "bun": "Bun_(software)",
    "postgresql": "PostgreSQL", "mongodb": "MongoDB", "redis": "Redis", "sqlite": "SQLite",
    "docker": "Docker_(software)", "kubernetes": "Kubernetes", "terraform": "Terraform_(software)",
    "pytorch": "PyTorch", "tensorflow": "TensorFlow", "langchain": "LangChain", "tailwindcss": "Tailwind_CSS",
    "php": "PHP", "ruby": "Ruby_(programming_language)", "csharp": "C_Sharp_(programming_language)",
    "scala": "Scala_(programming_language)", "dart": "Dart_(programming_language)", "r": "R_(programming_language)",
    "julia": "Julia_(programming_language)", "lua": "Lua", "haskell": "Haskell", "elixir": "Elixir_(programming_language)",
    "zig": "Zig_(programming_language)", "laravel": "Laravel", "rails": "Ruby_on_Rails", "aspnet-core": "ASP.NET_Core",
    "express": "Express.js", "nestjs": "NestJS", "flutter": "Flutter_(software)", "react-native": "React_Native",
    "jquery": "JQuery", "bootstrap": "Bootstrap_(front-end_framework)", "pandas": "Pandas_(software)", "numpy": "NumPy",
    "scikit-learn": "Scikit-learn", "keras": "Keras", "jupyter": "Project_Jupyter", "huggingface": "Hugging_Face",
    "mysql": "MySQL", "mariadb": "MariaDB", "elasticsearch": "Elasticsearch", "cassandra": "Apache_Cassandra",
    "neo4j": "Neo4j", "firebase": "Firebase", "supabase": "Supabase", "clickhouse": "ClickHouse", "duckdb": "DuckDB",
    "kafka": "Apache_Kafka", "rabbitmq": "RabbitMQ", "git": "Git", "linux": "Linux", "nginx": "Nginx",
    "ansible": "Ansible_(software)", "jenkins": "Jenkins_(software)", "prometheus": "Prometheus_(software)",
    "grafana": "Grafana", "aws": "Amazon_Web_Services", "azure": "Microsoft_Azure", "gcp": "Google_Cloud_Platform",
    "graphql": "GraphQL", "grpc": "GRPC", "webassembly": "WebAssembly", "webpack": "Webpack", "vite": "Vite_(software)",
    "vscode": "Visual_Studio_Code", "neovim": "Neovim", "postman": "Postman_(software)",
}


class WikipediaCollector(BaseCollector):
    source_name = "wikipedia"

    def __init__(self, client: httpx.Client | None = None, delay: float = 0.2, today: date | None = None):
        self.client = client or httpx.Client(timeout=20, headers={"User-Agent": USER_AGENT})
        self.delay = delay
        self.today = today

    def process(self, db: Session, source: Source, tech: Technology) -> int:
        title = WIKI_TITLES.get(tech.slug)
        if title is None:
            return 0
        end = (self.today or date.today()) - timedelta(days=1)          # today's count is not complete yet
        start = end - timedelta(days=29)
        url = f"{API}/{quote(title, safe='')}/daily/{start:%Y%m%d}/{end:%Y%m%d}"
        resp = self.client.get(url)
        if resp.status_code == 429:
            raise RateLimitError("Wikimedia rate limit")
        if resp.status_code == 404:
            log.warning("Wikipedia has no page views for %r (%s): check the title in WIKI_TITLES", title, tech.slug)
            return 0
        resp.raise_for_status()
        views = sum(item["views"] for item in resp.json().get("items", []))
        save_metric(db, tech.id, source.id, "wikipedia.views_30d", views)
        time.sleep(self.delay)
        return 1
