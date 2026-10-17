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
