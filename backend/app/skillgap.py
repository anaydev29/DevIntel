"""Skill-gap analysis: which technologies should this person learn next?

PRIORITY (0-100) for every technology the person does not know yet:
  priority = 100 x ( 0.55 x demand + 0.25 x momentum + 0.20 x fit )
  demand   = DevIntel Score / 100                      (how popular and active it is now)
  momentum = 30-day growth, capped (0% -> 0, 50%+ -> 1) (0 until enough history exists)
  fit      = how often it appears in the same dev.to articles as the person's skills,
             scaled to the best match (0 -> 1)           (builds on what they already know)
"""
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select

from app.cache import cached
from sqlalchemy.orm import Session

from app.models import Article, MetricSnapshot, TechScore, Technology, TechnologyAlias

W_DEMAND, W_MOMENTUM, W_FIT = 0.55, 0.25, 0.20
GROWTH_CAP = 0.5
TOP_N = 10


@cached(ttl=600)   # reads every recent article's tags, so reuse it for 10 minutes
def cooccurrence(db: Session, days: int = 60) -> dict[int, Counter]:
    """tech_id -> Counter(other tech_id -> number of recent articles tagged with both)."""
    names: dict[str, int] = {}
    for t in db.scalars(select(Technology)):
        names[t.slug] = t.id
        names[t.name.lower()] = t.id
    for a in db.scalars(select(TechnologyAlias)):
        names[a.alias] = a.technology_id
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    co: dict[int, Counter] = defaultdict(Counter)
    for (tags,) in db.execute(select(Article.tags).where(Article.source == "devto", Article.published_at >= cutoff)):
        ids = {names[t.lower()] for t in (tags or []) if isinstance(t, str) and t.lower() in names}
        for a in ids:
            for b in ids:
                if a != b:
                    co[a][b] += 1
    return co


def _starters(db: Session, tech_ids: list[int]) -> dict[int, list[dict]]:
    """Top 2 recent dev.to articles per technology, fetched for all technologies in one query."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    out: dict[int, list[dict]] = {i: [] for i in tech_ids}
    rows = db.scalars(select(Article).where(Article.source == "devto", Article.technology_id.in_(tech_ids),
                                            Article.published_at >= cutoff).order_by(Article.score.desc()))
    for a in rows:
        if len(out[a.technology_id]) < 2:
            out[a.technology_id].append({"title": a.title, "url": a.url})
    return out


def analyze(db: Session, known: dict[int, dict], category: str | None = None, limit: int = 8) -> dict:
    """`known` maps tech_id -> {"source": "manual"|"github"|"both", "repos": int|None}."""
    techs = {t.id: t for t in db.scalars(select(Technology))}
    latest_day = select(func.max(TechScore.computed_on)).scalar_subquery()    # one query for the newest scores
    scores = {s.technology_id: s for s in db.scalars(select(TechScore).where(TechScore.computed_on == latest_day))}

    known_out = [{"slug": techs[i].slug, "name": techs[i].name, "category": techs[i].category,
                  "devintel_score": scores[i].devintel_score if i in scores else None,
                  "growth_30d": scores[i].growth_30d if i in scores else None,
                  "source": info["source"], "repos": info.get("repos")}
                 for i, info in known.items()]
    known_out.sort(key=lambda k: k["devintel_score"] or 0, reverse=True)

    ranked = sorted(scores, key=lambda i: scores[i].devintel_score or 0, reverse=True)
    top10 = ranked[:TOP_N]
    coverage = {"known_in_top10": sum(1 for i in top10 if i in known), "top10": [techs[i].slug for i in top10]}
    if not scores:
        return {"known": known_out, "coverage": coverage, "recommendations": [],
                "note": "No scores yet. Run the data pipeline first."}

    rank_of = {i: n for n, i in enumerate(ranked, 1)}
    job_share: dict[int, float] = {}   # newest value of each technology's share of hiring-thread posts
    for tid, value in db.execute(select(MetricSnapshot.technology_id, MetricSnapshot.value).where(
            MetricSnapshot.metric == "hiring.share_pct",
            MetricSnapshot.captured_on >= date.today() - timedelta(days=45)).order_by(MetricSnapshot.captured_on)):
        job_share[tid] = value
    co = cooccurrence(db)
    candidates = [i for i in scores if i not in known and (not category or techs[i].category == category)]
    fit_raw = {i: sum(co[i][k] for k in known) for i in candidates}
    best_fit = max(fit_raw.values(), default=0) or 1

    recs = []
    for i in candidates:
        s = scores[i]
        demand = (s.devintel_score or 0) / 100
        momentum = 0.0 if s.growth_30d is None else max(0.0, min(1.0, s.growth_30d / GROWTH_CAP))
        fit = fit_raw[i] / best_fit
        priority = 100 * (W_DEMAND * demand + W_MOMENTUM * momentum + W_FIT * fit)

        related = sorted(((co[i][k], k) for k in known if co[i][k] > 0), reverse=True)[:2]
        reasons = []
        if related:
            top_count, top_k = related[0]
            reasons.append(f"Often used with {techs[top_k].name} ({top_count} recent articles mention both)")
        reasons.append(f"Ranked #{rank_of[i]} of {len(ranked)} by DevIntel Score")
        if job_share.get(i, 0) >= 3:
            reasons.append(f"Mentioned in {round(job_share[i])}% of recent Hacker News job posts")
        if s.is_emerging:
            reasons.append("Flagged as taking off")
        elif s.growth_30d is not None and s.growth_30d >= 0.15:
            reasons.append(f"Growing {round(s.growth_30d * 100)}% over 30 days")
        recs.append({"slug": techs[i].slug, "name": techs[i].name, "category": techs[i].category,
                     "priority": round(priority, 1), "devintel_score": s.devintel_score,
                     "growth_30d": s.growth_30d, "is_emerging": s.is_emerging, "reasons": reasons,
                     "related_to": [techs[k].name for _, k in related], "_id": i})
    recs.sort(key=lambda r: r["priority"], reverse=True)
    recs = recs[:limit]
    starters = _starters(db, [r["_id"] for r in recs]) if recs else {}
    for r in recs:
        r["starters"] = starters[r.pop("_id")]
    return {"known": known_out, "coverage": coverage, "recommendations": recs, "note": None}
