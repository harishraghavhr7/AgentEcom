"""
High-Performance In-Memory / Redis-compatible Aggressive Caching Engine.
Specifically designed for AI Agent throughput:
- Sub-millisecond reads
- SKU, Product ID, Category, and Search Query keying
- Reverse-index tracking for targeted webhook invalidations without TTL polling
- Cache hit/miss performance metrics
"""

import time
import asyncio
import hashlib
import json
from typing import Any, Dict, List, Optional, Set

class CacheMetrics:
    def __init__(self):
        self.hits: int = 0
        self.misses: int = 0
        self.invalidations: int = 0
        self.total_read_time_ms: float = 0.0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total) if total > 0 else 0.0

    @property
    def avg_read_latency_ms(self) -> float:
        return (self.total_read_time_ms / self.hits) if self.hits > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_pct": round(self.hit_rate * 100, 2),
            "invalidations": self.invalidations,
            "avg_hit_latency_ms": round(self.avg_read_latency_ms, 4),
        }


class CacheEntry:
    def __init__(self, value: Any, ttl_seconds: Optional[int] = None, tags: Optional[Set[str]] = None):
        self.value = value
        self.expires_at = time.time() + ttl_seconds if ttl_seconds else None
        self.tags = tags or set()

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class AgentCache:
    """
    Aggressive In-Memory Cache with Webhook-Based Invalidation.
    Maintains reverse indices by tags (SKUs, Categories) so invalidations
    are surgical and O(1) without requiring database polling or clearing the entire cache.
    """
    def __init__(self):
        self._store: Dict[str, CacheEntry] = {}
        self._tag_to_keys: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()
        self.metrics = CacheMetrics()

    def _generate_search_key(self, query: str, filters: Dict[str, Any]) -> str:
        payload = f"{query.strip().lower()}:{json.dumps(filters, sort_keys=True)}"
        return f"search:{hashlib.sha256(payload.encode()).hexdigest()[:16]}"

    async def get(self, key: str) -> Optional[Any]:
        start = time.perf_counter()
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self.metrics.misses += 1
                return None
            
            if entry.is_expired():
                del self._store[key]
                self.metrics.misses += 1
                return None
            
            elapsed_ms = (time.perf_counter() - start) * 1000
            self.metrics.hits += 1
            self.metrics.total_read_time_ms += elapsed_ms
            return entry.value

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = 3600,
        tags: Optional[List[str]] = None
    ) -> None:
        async with self._lock:
            tag_set = set(tags or [])
            self._store[key] = CacheEntry(value=value, ttl_seconds=ttl_seconds, tags=tag_set)
            
            for tag in tag_set:
                if tag not in self._tag_to_keys:
                    self._tag_to_keys[tag] = set()
                self._tag_to_keys[tag].add(key)

    async def invalidate_by_tag(self, tag: str) -> int:
        """
        Surgically invalidate all cache keys associated with a given tag
        (e.g., a specific SKU, Category, or Brand).
        """
        async with self._lock:
            keys_to_remove = self._tag_to_keys.pop(tag, set())
            removed_count = 0
            for key in keys_to_remove:
                if key in self._store:
                    del self._store[key]
                    removed_count += 1
            self.metrics.invalidations += removed_count
            return removed_count

    async def invalidate_sku(self, sku: str) -> int:
        """Invalidates product cache by SKU and all related search results."""
        count = await self.invalidate_by_tag(f"sku:{sku}")
        count += await self.invalidate_by_tag("search_results")
        return count

    async def invalidate_category(self, category_id: str) -> int:
        """Invalidates category cache and search results."""
        count = await self.invalidate_by_tag(f"category:{category_id}")
        count += await self.invalidate_by_tag("search_results")
        return count

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()
            self._tag_to_keys.clear()
            self.metrics.invalidations += 1

# Global cache singleton
cache = AgentCache()
