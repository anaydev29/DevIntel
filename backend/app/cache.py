"""Tiny in-process TTL cache for read-only endpoints.

The data only changes when the daily pipeline runs, so answers can be reused for a couple of minutes.
This matters most when the database is far away: a cache hit costs zero database round trips.
Set CACHE_SECONDS=0 to turn it off. Never use it on endpoints that depend on who is signed in."""
import threading
import time
from functools import wraps

from sqlalchemy.orm import Session

from app.config import settings

_stores: list[dict] = []


def cached(ttl: float | None = None):
    def decorate(fn):
        store: dict = {}
        lock = threading.Lock()
        _stores.append(store)

        @wraps(fn)  # keeps the original signature so FastAPI still sees the Depends() parameters
        def wrapper(*args, **kwargs):
            seconds = 0 if settings.cache_seconds <= 0 else (ttl or settings.cache_seconds)
            if seconds <= 0:
                return fn(*args, **kwargs)
            key = (tuple(a for a in args if not isinstance(a, Session)),
                   tuple(sorted((k, v) for k, v in kwargs.items() if not isinstance(v, Session))))
            now = time.monotonic()
            with lock:
                hit = store.get(key)
                if hit and hit[0] > now:
                    return hit[1]
            value = fn(*args, **kwargs)
            with lock:
                if len(store) > 500:
                    store.clear()
                store[key] = (now + seconds, value)
            return value
        return wrapper
    return decorate


def clear_caches() -> None:
    for store in _stores:
        store.clear()
