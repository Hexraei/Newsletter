"""In-memory TTL cache service with async support."""

import asyncio
import fnmatch
import functools
import inspect
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple


class TTLCache:
    """Async-compatible in-memory cache with per-key TTL.

    Thread-safe within a single event loop via ``asyncio.Lock``.
    Expired entries are cleaned up lazily on ``get()`` and periodically
    during any lock-holding operation.
    """

    def __init__(self, cleanup_interval: float = 300.0) -> None:
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._lock = asyncio.Lock()
        self._hits: int = 0
        self._misses: int = 0
        self._cleanup_interval = cleanup_interval
        self._last_cleanup: float = time.monotonic()

    async def get(self, key: str) -> Any:
        """Return cached value or ``None`` on miss / expiry."""
        async with self._lock:
            self._lazy_cleanup()
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                self._misses += 1
                return None
            self._hits += 1
            return value

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Store *value* under *key* with the given TTL."""
        async with self._lock:
            self._store[key] = (value, time.monotonic() + ttl_seconds)

    async def delete(self, key: str) -> bool:
        """Delete a single key.  Returns ``True`` if it existed."""
        async with self._lock:
            return self._store.pop(key, None) is not None

    async def invalidate(self, pattern: str) -> int:
        """Remove all keys matching a glob *pattern*.  Returns count removed."""
        async with self._lock:
            to_remove = [k for k in self._store if fnmatch.fnmatch(k, pattern)]
            for k in to_remove:
                del self._store[k]
            return len(to_remove)

    async def clear(self) -> None:
        """Drop every entry and reset hit/miss counters."""
        async with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0

    async def stats(self) -> Dict[str, Any]:
        """Return hit/miss counts, key count, and rough memory estimate."""
        async with self._lock:
            self._purge_expired()
            total = self._hits + self._misses
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total, 4) if total else 0.0,
                "total_keys": len(self._store),
                "memory_estimate_bytes": sum(
                    sys.getsizeof(k) + sys.getsizeof(v)
                    for k, (v, _) in self._store.items()
                ),
            }

    # -- internal helpers (caller must already hold the lock) --------------

    def _lazy_cleanup(self) -> None:
        now = time.monotonic()
        if now - self._last_cleanup > self._cleanup_interval:
            self._purge_expired()
            self._last_cleanup = now

    def _purge_expired(self) -> None:
        now = time.monotonic()
        expired = [k for k, (_, exp) in self._store.items() if now > exp]
        for k in expired:
            del self._store[k]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_cache_instance: Optional[TTLCache] = None


def get_cache() -> TTLCache:
    """Return the global singleton ``TTLCache`` instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = TTLCache()
    return _cache_instance


# ---------------------------------------------------------------------------
# Cache-key helpers
# ---------------------------------------------------------------------------
_SKIP_TYPES: Optional[Tuple[type, ...]] = None


def _init_skip_types() -> Tuple[type, ...]:
    """Lazily resolve types that should be excluded from cache keys."""
    global _SKIP_TYPES
    if _SKIP_TYPES is not None:
        return _SKIP_TYPES
    skip: List[type] = []
    try:
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: WPS433
        skip.append(AsyncSession)
    except ImportError:
        pass
    try:
        from starlette.requests import Request  # noqa: WPS433
        skip.append(Request)
    except ImportError:
        pass
    _SKIP_TYPES = tuple(skip)
    return _SKIP_TYPES


def _serialize_value(value: Any) -> str:
    """Convert a single parameter value to a stable cache-key fragment."""
    if value is None:
        return "_"
    if isinstance(value, (list, tuple)):
        return ",".join(sorted(str(v) for v in value)) or "_empty"
    if hasattr(value, "id"):
        # ORM models (e.g. User) — use the primary key
        return str(value.id)
    return str(value)


def _build_cache_key(prefix: str, func: Callable, args: tuple, kwargs: dict) -> str:
    skip = _init_skip_types()
    sig = inspect.signature(func)
    bound = sig.bind(*args, **kwargs)
    bound.apply_defaults()

    parts: List[str] = [prefix]
    for name, value in bound.arguments.items():
        if isinstance(value, skip):
            continue
        parts.append(f"{name}={_serialize_value(value)}")
    return ":".join(parts)


# ---------------------------------------------------------------------------
# @cached decorator
# ---------------------------------------------------------------------------

def cached(ttl: int, key_prefix: str) -> Callable:
    """Decorator that caches async function results with a TTL.

    * Builds a cache key from *key_prefix* + all hashable function args.
    * DB sessions and Request objects are automatically excluded from the key.
    * ORM model instances (e.g. ``User``) are represented by their ``.id``.
    * ``None`` results are **not** cached.
    * Works with both sync and async functions (sync functions skip caching).
    """

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                cache = get_cache()
                key: Optional[str] = None
                try:
                    key = _build_cache_key(key_prefix, func, args, kwargs)
                    hit = await cache.get(key)
                    if hit is not None:
                        return hit
                except Exception:
                    pass  # degrade gracefully — treat as cache miss

                result = await func(*args, **kwargs)

                if result is not None and key is not None:
                    try:
                        await cache.set(key, result, ttl)
                    except Exception:
                        pass
                return result

            return wrapper
        else:
            # Sync path — no caching (all FastAPI endpoints here are async)
            return func

    return decorator


# ---------------------------------------------------------------------------
# Feed-specific invalidation helper
# ---------------------------------------------------------------------------

async def invalidate_feed_caches() -> int:
    """Invalidate all feed-related cache entries.

    Intended to be called by scrapers after ingesting new content.
    """
    cache = get_cache()
    return await cache.invalidate("feed:*")
