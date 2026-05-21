"""
Caching Layer with Redis Integration

Implements multi-level caching for performance optimization.
Includes cache warming, invalidation strategies, and metrics.
"""

import logging
from typing import Any, Dict, Optional, Callable, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import hashlib
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    ttl_seconds: int
    created_at: datetime
    accessed_at: datetime
    access_count: int = 0
    tags: List[str] = None

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl_seconds <= 0:
            return False
        elapsed = (datetime.utcnow() - self.created_at).total_seconds()
        return elapsed > self.ttl_seconds

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "ttl_seconds": self.ttl_seconds,
            "created_at": self.created_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "access_count": self.access_count,
            "age_seconds": (datetime.utcnow() - self.created_at).total_seconds(),
        }


class InMemoryCache:
    """In-memory cache with LRU eviction."""

    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self.cache:
            self.misses += 1
            return None

        entry = self.cache[key]

        if entry.is_expired():
            del self.cache[key]
            self.misses += 1
            return None

        entry.access_count += 1
        entry.accessed_at = datetime.utcnow()
        self.hits += 1

        return entry.value

    async def set(
        self, key: str, value: Any, ttl_seconds: int = 3600, tags: List[str] = None
    ) -> None:
        """Set value in cache."""
        if len(self.cache) >= self.max_size:
            # Evict least recently used
            lru_key = min(
                self.cache.keys(),
                key=lambda k: self.cache[k].accessed_at,
            )
            del self.cache[lru_key]

        self.cache[key] = CacheEntry(
            key=key,
            value=value,
            ttl_seconds=ttl_seconds,
            created_at=datetime.utcnow(),
            accessed_at=datetime.utcnow(),
            tags=tags or [],
        )

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    async def clear_by_tag(self, tag: str) -> int:
        """Clear all entries with tag."""
        keys_to_delete = [
            k for k, v in self.cache.items() if tag in (v.tags or [])
        ]
        for key in keys_to_delete:
            del self.cache[key]
        return len(keys_to_delete)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (
            self.hits / total_requests if total_requests > 0 else 0
        )

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "entries": [v.to_dict() for v in self.cache.values()],
        }


class CacheKey:
    """Cache key generator."""

    @staticmethod
    def generate(prefix: str, *args, **kwargs) -> str:
        """Generate cache key."""
        key_parts = [prefix] + [str(a) for a in args]
        key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])

        key_string = "|".join(key_parts)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()

        return f"{prefix}:{key_hash}"


class CacheWarmer:
    """Pre-loads cache with frequently accessed data."""

    def __init__(self, cache: InMemoryCache):
        self.cache = cache
        self.warm_functions: Dict[str, Callable] = {}

    def register_warmup_fn(self, key_prefix: str, fn: Callable) -> None:
        """Register a function to warm cache."""
        self.warm_functions[key_prefix] = fn

    async def warm_cache(self) -> Dict[str, int]:
        """Warm cache with all registered functions."""
        logger.info("Warming cache...")

        results = {}
        for key_prefix, fn in self.warm_functions.items():
            try:
                data = await fn()
                if isinstance(data, dict):
                    for key, value in data.items():
                        await self.cache.set(
                            f"{key_prefix}:{key}",
                            value,
                            ttl_seconds=3600,
                            tags=[key_prefix],
                        )
                    results[key_prefix] = len(data)
                else:
                    await self.cache.set(key_prefix, data, ttl_seconds=3600)
                    results[key_prefix] = 1

                logger.info(f"Warmed {key_prefix}: {results[key_prefix]} entries")
            except Exception as e:
                logger.error(f"Cache warming failed for {key_prefix}: {e}")
                results[key_prefix] = 0

        return results


class CacheInvalidator:
    """Manages cache invalidation strategies."""

    def __init__(self, cache: InMemoryCache):
        self.cache = cache
        self.invalidation_rules: Dict[str, List[str]] = {}

    def register_invalidation_rule(self, trigger_tag: str, invalidate_tags: List[str]) -> None:
        """Register invalidation rule."""
        self.invalidation_rules[trigger_tag] = invalidate_tags

    async def invalidate(self, trigger_tag: str) -> int:
        """Invalidate cache based on rules."""
        if trigger_tag not in self.invalidation_rules:
            return 0

        invalidate_tags = self.invalidation_rules[trigger_tag]
        total_invalidated = 0

        for tag in invalidate_tags:
            count = await self.cache.clear_by_tag(tag)
            total_invalidated += count

        logger.info(
            f"Invalidated {total_invalidated} entries for trigger: {trigger_tag}"
        )
        return total_invalidated


class CachedFunction:
    """Decorator for caching function results."""

    def __init__(
        self,
        cache: InMemoryCache,
        ttl_seconds: int = 3600,
        key_prefix: str = "",
    ):
        self.cache = cache
        self.ttl_seconds = ttl_seconds
        self.key_prefix = key_prefix

    def __call__(self, fn: Callable) -> Callable:
        """Wrap function with caching."""
        async def wrapper(*args, **kwargs):
            cache_key = CacheKey.generate(
                self.key_prefix or fn.__name__, *args, **kwargs
            )

            # Try to get from cache
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return cached

            # Execute function
            result = await fn(*args, **kwargs)

            # Store in cache
            await self.cache.set(
                cache_key,
                result,
                ttl_seconds=self.ttl_seconds,
                tags=[self.key_prefix or fn.__name__],
            )

            return result

        return wrapper


class QueryCache:
    """Specialized caching for database queries."""

    def __init__(self, cache: InMemoryCache):
        self.cache = cache
        self.query_stats: Dict[str, Dict[str, int]] = {}

    async def get_query_result(
        self, query_hash: str, execute_fn: Callable
    ) -> Any:
        """Get query result with caching."""
        cached = await self.cache.get(query_hash)
        if cached is not None:
            self._record_hit(query_hash)
            return cached

        result = await execute_fn()
        await self.cache.set(
            query_hash, result, ttl_seconds=300, tags=["query"]
        )

        self._record_miss(query_hash)
        return result

    def _record_hit(self, query_hash: str) -> None:
        """Record cache hit for query."""
        if query_hash not in self.query_stats:
            self.query_stats[query_hash] = {"hits": 0, "misses": 0}
        self.query_stats[query_hash]["hits"] += 1

    def _record_miss(self, query_hash: str) -> None:
        """Record cache miss for query."""
        if query_hash not in self.query_stats:
            self.query_stats[query_hash] = {"hits": 0, "misses": 0}
        self.query_stats[query_hash]["misses"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get query cache statistics."""
        return {
            "queries": len(self.query_stats),
            "stats": self.query_stats,
        }


class MultiLevelCache:
    """Coordinates multiple cache levels."""

    def __init__(self, memory_cache: InMemoryCache):
        self.memory_cache = memory_cache
        self.warmer = CacheWarmer(memory_cache)
        self.invalidator = CacheInvalidator(memory_cache)
        self.query_cache = QueryCache(memory_cache)

    async def initialize(self) -> None:
        """Initialize cache system."""
        logger.info("Initializing multi-level cache...")
        await self.warmer.warm_cache()

    async def get(self, key: str) -> Optional[Any]:
        """Get from cache."""
        return await self.memory_cache.get(key)

    async def set(
        self, key: str, value: Any, ttl_seconds: int = 3600, tags: List[str] = None
    ) -> None:
        """Set in cache."""
        await self.memory_cache.set(key, value, ttl_seconds, tags)

    async def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate by tag."""
        return await self.memory_cache.clear_by_tag(tag)

    def get_all_stats(self) -> Dict[str, Any]:
        """Get all cache statistics."""
        return {
            "memory_cache": self.memory_cache.get_stats(),
            "query_cache": self.query_cache.get_stats(),
        }
