from app.config import settings

settings.cache_seconds = 0  # tests must see fresh data; the cache has its own tests that switch it on
