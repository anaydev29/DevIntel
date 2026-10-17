"""Analysis step: turns raw metric snapshots into the DevIntel Score and the emerging flag.

DEVINTEL SCORE (0-100), computed from the latest snapshot of each signal
  1. For every signal, each technology gets a percentile rank among all technologies
     (0 = lowest, 1 = highest). Ranks are robust to huge outliers (Python vs Bun).
  2. Score = weighted average of the technology's ranks x 100.
     If a source has no data for a technology, the remaining weights are re-normalized.

GROWTH (growth_30d)
  For three signals, compare the latest value with the oldest snapshot inside the last
  30 days (needs at least MIN_HISTORY_DAYS of history), scale to a 30-day rate, then take
  a weighted average. No history yet -> growth is None and nothing is flagged.

EMERGING FLAG - a technology is emerging only if ALL are true:
  - it is in the "established enough" pool (score >= MIN_SCORE), so tiny repos cannot spike
  - growth_30d >= MIN_GROWTH
  - at least MIN_POSITIVE_SIGNALS of the growth signals are positive (cross-source agreement)
  - its growth is in the top EMERGING_TOP_FRACTION of that pool
"""
from bisect import bisect_left, bisect_right
from collections import defaultdict
from datetime import date, timedelta
from math import ceil

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MetricSnapshot, TechScore

SCORE_WEIGHTS = {
    "stackoverflow.questions_30d": 0.30,
    "github.repo_count": 0.20,
    "github.top_stars": 0.15,
    "hackernews.stories_30d": 0.15,
    "stackoverflow.total_questions": 0.10,
    "hackernews.points_30d": 0.10,
}
GROWTH_WEIGHTS = {
    "github.repo_count": 0.4,
    "stackoverflow.questions_30d": 0.4,
    "hackernews.stories_30d": 0.2,
}
TARGET_WINDOW_DAYS = 30
MIN_HISTORY_DAYS = 7
STALE_AFTER_DAYS = 7
MIN_SCORE = 20.0
MIN_GROWTH = 0.05
MIN_POSITIVE_SIGNALS = 2
EMERGING_TOP_FRACTION = 0.2


def percentile_ranks(values: dict[int, float]) -> dict[int, float]:
    n = len(values)
    if n == 0:
        return {}
    if n == 1:
        return {k: 0.5 for k in values}
    ordered = sorted(values.values())
    out = {}
    for k, v in values.items():
        less = bisect_left(ordered, v)
        equal = bisect_right(ordered, v) - less
        out[k] = (less + (equal - 1) / 2) / (n - 1)  # ties share the average rank
    return out


def growth_rate(points: list[tuple[date, float]]) -> float | None:
    """30-day growth rate from a sorted [(date, value)] series, or None if history is too short."""
    d1, v1 = points[-1]
    window = [(d, v) for d, v in points if (d1 - d).days <= TARGET_WINDOW_DAYS]
    d0, v0 = window[0]
    gap = (d1 - d0).days
    if gap < MIN_HISTORY_DAYS or v0 <= 0:
        return None
    return (v1 / v0) ** (TARGET_WINDOW_DAYS / gap) - 1


def _load_series(db: Session, today: date) -> dict[tuple[int, str], list[tuple[date, float]]]:
    rows = db.execute(
        select(MetricSnapshot.technology_id, MetricSnapshot.metric,
               MetricSnapshot.captured_on, MetricSnapshot.value)
        .where(MetricSnapshot.captured_on >= today - timedelta(days=60),
               MetricSnapshot.captured_on <= today)
        .order_by(MetricSnapshot.captured_on))
    series: dict[tuple[int, str], list[tuple[date, float]]] = defaultdict(list)
    for tid, metric, day, value in rows:
        series[(tid, metric)].append((day, value))
    return series


def compute_scores(db: Session, today: date | None = None) -> dict:
    today = today or date.today()
    series = _load_series(db, today)

    # ---- DevIntel Score ----
    latest: dict[str, dict[int, float]] = defaultdict(dict)
    for (tid, metric), pts in series.items():
        day, value = pts[-1]
        if metric in SCORE_WEIGHTS and (today - day).days <= STALE_AFTER_DAYS:
            latest[metric][tid] = value
    ranks = {m: percentile_ranks(vals) for m, vals in latest.items()}
    tech_ids = {tid for r in ranks.values() for tid in r}
    scores: dict[int, float] = {}
    for tid in tech_ids:
        num = den = 0.0
        for metric, weight in SCORE_WEIGHTS.items():
            if tid in ranks.get(metric, {}):
                num += weight * ranks[metric][tid]
                den += weight
        scores[tid] = 100 * num / den

    # ---- Growth ----
    growth: dict[int, float] = {}
    positives: dict[int, int] = {}
    for tid in tech_ids:
        num = den = 0.0
        pos = 0
        for metric, weight in GROWTH_WEIGHTS.items():
            pts = series.get((tid, metric))
            if not pts or (today - pts[-1][0]).days > STALE_AFTER_DAYS:
                continue
            g = growth_rate(pts)
            if g is None:
                continue
            num += weight * g
            den += weight
            pos += g > 0
        if den:
            growth[tid] = num / den
            positives[tid] = pos

    # ---- Emerging flag ----
    pool = {t: g for t, g in growth.items() if scores[t] >= MIN_SCORE}
    emerging: set[int] = set()
    if pool:
        keep = max(1, ceil(EMERGING_TOP_FRACTION * len(pool)))
        cutoff = sorted(pool.values(), reverse=True)[keep - 1]
        emerging = {t for t, g in pool.items()
                    if g >= cutoff and g >= MIN_GROWTH and positives[t] >= MIN_POSITIVE_SIGNALS}

    # ---- Save (one row per technology per day; safe to re-run) ----
    for tid, score in scores.items():
        row = db.scalar(select(TechScore).where(TechScore.technology_id == tid,
                                                TechScore.computed_on == today))
        if not row:
            row = TechScore(technology_id=tid, computed_on=today)
            db.add(row)
        row.devintel_score = round(score, 2)
        row.growth_30d = round(growth[tid], 4) if tid in growth else None
        row.is_emerging = tid in emerging
    db.commit()
    return {"scored": len(scores), "with_growth": len(growth), "emerging": len(emerging)}
