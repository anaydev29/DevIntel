"""Backtest of the "Taking off" flag: did flagged technologies really keep growing?

METHOD
  For every day a technology was flagged as emerging, look HORIZON days ahead (the flag itself only used data from
  before that day, so this is a fair test). Forward growth = the weighted change of the same activity signals the
  flag uses (GitHub repositories, Stack Overflow questions, Wikipedia views, Hacker News stories) between the flag
  day and flag day + HORIZON.
  A flag is a HIT if the technology grew faster than the MEDIAN technology over the same days. By definition half of
  all technologies beat the median, so 50% is what a random pick would score.
  Repeated flags of the same technology within HORIZON days count once (they are one event, not many).
  The hit rate comes with a 95% Wilson interval, because with only a handful of flags the number is very uncertain.
"""
from bisect import bisect_right
from collections import defaultdict
from datetime import date, timedelta
from math import sqrt
from statistics import median

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analysis import GROWTH_WEIGHTS
from app.models import MetricSnapshot, TechScore, Technology

HORIZONS = (7, 14, 30)
LOOKBACK_DAYS = 200
MAX_STALE_DAYS = 3       # a snapshot up to 3 days older than the target day still counts


def wilson(hits: int, n: int, z: float = 1.96) -> tuple[float | None, float | None]:
    """95% confidence interval for a share (better behaved than the simple formula when n is small)."""
    if n == 0:
        return None, None
    p = hits / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


class _Series:
    def __init__(self, points: list[tuple[date, float]]):
        points.sort()
        self.days = [d for d, _ in points]
        self.values = [v for _, v in points]

    def at(self, day: date) -> float | None:
        i = bisect_right(self.days, day) - 1
        if i < 0 or (day - self.days[i]).days > MAX_STALE_DAYS:
            return None
        return self.values[i]


def _forward_growth(series: dict[tuple[int, str], _Series], tid: int, start: date, horizon: int) -> float | None:
    num = den = 0.0
    for metric, weight in GROWTH_WEIGHTS.items():
        s = series.get((tid, metric))
        if s is None:
            continue
        v0, v1 = s.at(start), s.at(start + timedelta(days=horizon))
        if v0 and v0 > 0 and v1 is not None:
            num += weight * (v1 / v0 - 1)
            den += weight
    return num / den if den else None


def run_backtest(db: Session, horizon: int = 14) -> dict:
    latest = db.scalar(select(func.max(MetricSnapshot.captured_on)))
    earliest = db.scalar(select(func.min(MetricSnapshot.captured_on)))
    base = {"horizon_days": horizon, "latest_data_date": latest, "baseline": 0.5, "flags": 0, "hits": 0, "hit_rate": None,
            "ci_low": None, "ci_high": None, "avg_forward_growth_flagged": None, "avg_forward_growth_all": None, "events": []}
    if latest is None:
        return {**base, "status": "no_data", "message": "No data has been collected yet."}

    series_points: dict[tuple[int, str], list[tuple[date, float]]] = defaultdict(list)
    for tid, metric, day, value in db.execute(select(MetricSnapshot.technology_id, MetricSnapshot.metric, MetricSnapshot.captured_on,
                                                     MetricSnapshot.value).where(MetricSnapshot.metric.in_(list(GROWTH_WEIGHTS)),
                                                     MetricSnapshot.captured_on >= latest - timedelta(days=LOOKBACK_DAYS))):
        series_points[(tid, metric)].append((day, value))
    series = {k: _Series(v) for k, v in series_points.items()}
    tech_ids = sorted({tid for tid, _ in series})

    flagged = db.execute(select(TechScore.technology_id, TechScore.computed_on).where(TechScore.is_emerging.is_(True))
                         .order_by(TechScore.technology_id, TechScore.computed_on)).all()
    all_flag_days = [d for _, d in flagged]
    # one event per technology per horizon window
    events_raw: list[tuple[int, date]] = []
    last_kept: dict[int, date] = {}
    for tid, day in flagged:
        if tid in last_kept and (day - last_kept[tid]).days < horizon:
            continue
        last_kept[tid] = day
        events_raw.append((tid, day))
    judgeable = [(tid, day) for tid, day in events_raw if day + timedelta(days=horizon) <= latest]

    if not judgeable:
        if all_flag_days:
            first_judge = min(all_flag_days) + timedelta(days=horizon)
            msg = (f"{len(events_raw)} technolog{'y has' if len(events_raw) == 1 else 'ies have'} been flagged so far, but none is "
                   f"{horizon} days old yet. The first can be judged on {first_judge:%d %b %Y}.")
        else:
            first_possible = (earliest or latest) + timedelta(days=7 + horizon)
            msg = (f"No technology has been flagged as taking off yet. Flags need 7 days of data, and each flag then needs "
                   f"{horizon} more days to be judged, so the first result can appear around {first_possible:%d %b %Y}.")
        return {**base, "status": "waiting", "message": msg}

    median_cache: dict[date, tuple[float, float]] = {}

    def market(day: date) -> tuple[float, float] | None:
        if day not in median_cache:
            growths = [g for g in (_forward_growth(series, t, day, horizon) for t in tech_ids) if g is not None]
            median_cache[day] = (median(growths), sum(growths) / len(growths)) if growths else None
        return median_cache[day]

    names = {t.id: t for t in db.scalars(select(Technology).where(Technology.id.in_({t for t, _ in judgeable})))}
    events, hits = [], 0
    for tid, day in judgeable:
        g, mk = _forward_growth(series, tid, day, horizon), market(day)
        if g is None or mk is None:
            continue
        beat = g > mk[0]
        hits += beat
        events.append({"slug": names[tid].slug, "technology": names[tid].name, "flagged_on": day, "forward_growth": g,
                       "median_growth": mk[0], "beat_median": beat})
    if not events:
        return {**base, "status": "waiting", "message": "Flags exist, but there is not enough data around them to judge yet."}

    n = len(events)
    low, high = wilson(hits, n)
    avg_flagged = sum(e["forward_growth"] for e in events) / n
    avg_all = sum(market(e["flagged_on"])[1] for e in events) / n
    events.sort(key=lambda e: e["flagged_on"], reverse=True)
    return {**base, "status": "ready", "message": "", "flags": n, "hits": hits, "hit_rate": hits / n, "ci_low": low, "ci_high": high,
            "avg_forward_growth_flagged": avg_flagged, "avg_forward_growth_all": avg_all, "events": events}
