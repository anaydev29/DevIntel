import time
import inspect
from functools import wraps

# Global cache store: key -> (expiry_time, value)
_store: dict = {}


def clear_caches():
    """Empty the in-memory cache. Used by the test suite to start each test clean."""
    _store.clear()


def cached(ttl: float | None = None):
    """Serve a function's result from an in-memory cache for `ttl` seconds.
    The cache key is built from the function name + its *real* arguments,
    but middleware/dependency args (request, db) are EXCLUDED so the key
    stays identical across calls (this is what makes the repeat request free)."""
    SKIP = {"request", "db"}  # never part of the cache key

    def decorator(func):
        sig = inspect.signature(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            from app.config import settings
            seconds = ttl if ttl is not None else settings.cache_seconds
            if not seconds:
                return func(*args, **kwargs)

            # Build a key from only the non-skipped, hashable params
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            key_parts = [func.__qualname__]
            for name, value in bound.arguments.items():
                if name in SKIP:
                    continue
                try:
                    hash(value)
                    key_parts.append((name, value))
                except TypeError:
                    pass  # skip unhashable objects (Session, Request, etc.)

            key = repr(key_parts)
            now = time.time()
            hit = _store.get(key)
            if hit and hit[0] > now:
                return hit[1]

            result = func(*args, **kwargs)
            _store[key] = (now + seconds, result)
            return result
        return wrapper
    return decorator