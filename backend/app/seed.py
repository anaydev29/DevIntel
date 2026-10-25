"""Seed the technology catalog. Run: python -m app.seed  (safe to re-run)."""
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Technology, TechnologyAlias
from app.normalize import clean

# (slug, name, category, github_topic, stackoverflow_tag, [aliases])
CATALOG = [
    ("python", "Python", "language", "python", "python", ["py", "python3"]),
    ("javascript", "JavaScript", "language", "javascript", "javascript", ["js", "ecmascript"]),
    ("typescript", "TypeScript", "language", "typescript", "typescript", ["ts"]),
    ("java", "Java", "language", "java", "java", []),
    ("go", "Go", "language", "golang", "go", ["golang"]),
    ("rust", "Rust", "language", "rust", "rust", ["rust-lang"]),
    ("kotlin", "Kotlin", "language", "kotlin", "kotlin", []),
    ("swift", "Swift", "language", "swift", "swift", ["swift-lang"]),
    ("cpp", "C++", "language", "cpp", "c++", ["c++", "cplusplus"]),
    ("react", "React", "framework", "react", "reactjs", ["reactjs", "react.js"]),
    ("vue", "Vue.js", "framework", "vue", "vue.js", ["vuejs", "vue.js"]),
    ("angular", "Angular", "framework", "angular", "angular", ["angularjs"]),
    ("svelte", "Svelte", "framework", "svelte", "svelte", ["sveltekit"]),
    ("nextjs", "Next.js", "framework", "nextjs", "next.js", ["next.js", "next"]),
    ("django", "Django", "framework", "django", "django", []),
    ("fastapi", "FastAPI", "framework", "fastapi", "fastapi", []),
    ("flask", "Flask", "framework", "flask", "flask", []),
    ("spring-boot", "Spring Boot", "framework", "spring-boot", "spring-boot", ["springboot"]),
    ("nodejs", "Node.js", "runtime", "nodejs", "node.js", ["node", "node.js"]),
    ("deno", "Deno", "runtime", "deno", "deno", []),
    ("bun", "Bun", "runtime", "bun", "bun", ["bunjs"]),
    ("postgresql", "PostgreSQL", "database", "postgresql", "postgresql", ["postgres", "psql"]),
    ("mongodb", "MongoDB", "database", "mongodb", "mongodb", ["mongo"]),
    ("redis", "Redis", "database", "redis", "redis", []),
    ("sqlite", "SQLite", "database", "sqlite", "sqlite", []),
    ("docker", "Docker", "devops", "docker", "docker", []),
    ("kubernetes", "Kubernetes", "devops", "kubernetes", "kubernetes", ["k8s"]),
    ("terraform", "Terraform", "devops", "terraform", "terraform", []),
    ("pytorch", "PyTorch", "ai-ml", "pytorch", "pytorch", ["torch"]),
    ("tensorflow", "TensorFlow", "ai-ml", "tensorflow", "tensorflow", ["tf"]),
    ("langchain", "LangChain", "ai-ml", "langchain", "langchain", []),
    ("tailwindcss", "Tailwind CSS", "tool", "tailwindcss", "tailwind-css", ["tailwind"]),
    # ---- added to grow the catalog from 32 to 87 technologies ----
    ("php", "PHP", "language", "php", "php", []),
    ("ruby", "Ruby", "language", "ruby", "ruby", ["ruby-lang"]),
    ("csharp", "C#", "language", "csharp", "c#", ["c-sharp", "dotnet"]),
    ("scala", "Scala", "language", "scala", "scala", []),
    ("dart", "Dart", "language", "dart", "dart", ["dartlang"]),
    ("r", "R", "language", "rstats", "r", ["rstats", "r-lang"]),
    ("julia", "Julia", "language", "julia", "julia", ["julialang"]),
    ("lua", "Lua", "language", "lua", "lua", []),
    ("haskell", "Haskell", "language", "haskell", "haskell", []),
    ("elixir", "Elixir", "language", "elixir", "elixir", []),
    ("zig", "Zig", "language", "zig", "zig", ["ziglang"]),
    ("laravel", "Laravel", "framework", "laravel", "laravel", []),
    ("rails", "Ruby on Rails", "framework", "rails", "ruby-on-rails", ["ror", "ruby-on-rails"]),
    ("aspnet-core", "ASP.NET Core", "framework", "aspnet-core", "asp.net-core", ["asp.net", "asp.net core", ".net core"]),
    ("express", "Express", "framework", "expressjs", "express", ["expressjs", "express.js"]),
    ("nestjs", "NestJS", "framework", "nestjs", "nestjs", ["nest.js", "nest"]),
    ("flutter", "Flutter", "framework", "flutter", "flutter", []),
    ("react-native", "React Native", "framework", "react-native", "react-native", ["reactnative", "rn"]),
    ("jquery", "jQuery", "framework", "jquery", "jquery", []),
    ("bootstrap", "Bootstrap", "framework", "bootstrap", "twitter-bootstrap", []),
    ("pandas", "pandas", "ai-ml", "pandas", "pandas", []),
    ("numpy", "NumPy", "ai-ml", "numpy", "numpy", []),
    ("scikit-learn", "scikit-learn", "ai-ml", "scikit-learn", "scikit-learn", ["sklearn", "scikit learn"]),
    ("keras", "Keras", "ai-ml", "keras", "keras", []),
    ("jupyter", "Jupyter", "ai-ml", "jupyter-notebook", "jupyter-notebook", ["jupyter notebook", "ipython"]),
    ("huggingface", "Hugging Face", "ai-ml", "huggingface", "huggingface-transformers", ["hugging face", "transformers"]),
    ("mysql", "MySQL", "database", "mysql", "mysql", []),
    ("mariadb", "MariaDB", "database", "mariadb", "mariadb", []),
    ("elasticsearch", "Elasticsearch", "database", "elasticsearch", "elasticsearch", ["elastic"]),
    ("cassandra", "Cassandra", "database", "cassandra", "cassandra", ["apache cassandra"]),
    ("neo4j", "Neo4j", "database", "neo4j", "neo4j", []),
    ("firebase", "Firebase", "database", "firebase", "firebase", []),
    ("supabase", "Supabase", "database", "supabase", "supabase", []),
    ("clickhouse", "ClickHouse", "database", "clickhouse", "clickhouse", []),
    ("duckdb", "DuckDB", "database", "duckdb", "duckdb", []),
    ("kafka", "Kafka", "tool", "kafka", "apache-kafka", ["apache kafka"]),
    ("rabbitmq", "RabbitMQ", "tool", "rabbitmq", "rabbitmq", []),
    ("git", "Git", "devops", "git", "git", []),
    ("linux", "Linux", "devops", "linux", "linux", []),
    ("nginx", "Nginx", "devops", "nginx", "nginx", []),
    ("ansible", "Ansible", "devops", "ansible", "ansible", []),
    ("jenkins", "Jenkins", "devops", "jenkins", "jenkins", []),
    ("prometheus", "Prometheus", "devops", "prometheus", "prometheus", []),
    ("grafana", "Grafana", "devops", "grafana", "grafana", []),
    ("aws", "AWS", "devops", "aws", "amazon-web-services", ["amazon web services"]),
    ("azure", "Azure", "devops", "azure", "azure", ["microsoft azure"]),
    ("gcp", "Google Cloud", "devops", "google-cloud", "google-cloud-platform", ["gcp", "google cloud platform"]),
    ("graphql", "GraphQL", "tool", "graphql", "graphql", []),
    ("grpc", "gRPC", "tool", "grpc", "grpc", []),
    ("webassembly", "WebAssembly", "tool", "webassembly", "webassembly", ["wasm"]),
    ("webpack", "Webpack", "tool", "webpack", "webpack", []),
    ("vite", "Vite", "tool", "vite", "vite", ["vitejs"]),
    ("vscode", "VS Code", "tool", "vscode", "visual-studio-code", ["visual studio code", "vs code"]),
    ("neovim", "Neovim", "tool", "neovim", "neovim", ["nvim"]),
    ("postman", "Postman", "tool", "postman", "postman", []),
]


def seed(db) -> int:
    added = 0
    for slug, name, cat, topic, so_tag, aliases in CATALOG:
        tech = db.scalar(select(Technology).where(Technology.slug == slug))
        if not tech:
            tech = Technology(slug=slug, name=name, category=cat,
                              github_topic=topic, stackoverflow_tag=so_tag)
            db.add(tech)
            db.flush()
            added += 1
        existing = {a.alias for a in tech.aliases}
        for a in {clean(x) for x in aliases + [name]}:
            if a != slug and a not in existing:
                taken = db.scalar(select(TechnologyAlias).where(TechnologyAlias.alias == a))
                if not taken:
                    tech.aliases.append(TechnologyAlias(alias=a))
    db.commit()
    return added


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        print(f"Seeded {seed(session)} new technologies")
