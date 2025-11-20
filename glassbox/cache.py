"""
GlassBox Caching Layer - Improves performance for frequently accessed data.

Provides in-memory LRU caching for:
- Model instances (avoid reloading)
- Trace results (hot traces)
- Analysis results (decision probabilities, attention patterns)
"""

from functools import lru_cache
from typing import Dict, Any, Optional, List
import hashlib
import json
from pathlib import Path
from datetime import datetime, timedelta

from glassbox.logging_config import get_logger

logger = get_logger(__name__)


class TraceCache:
    """
    In-memory cache for trace results and analysis data.

    Uses LRU eviction policy to keep memory usage bounded.
    Caches hot traces to avoid repeated file I/O.
    """

    def __init__(self, max_size: int = 100, ttl_minutes: int = 60):
        """
        Initialize trace cache.

        Args:
            max_size: Maximum number of traces to cache (default: 100)
            ttl_minutes: Time-to-live for cached entries in minutes (default: 60)
        """
        self.max_size = max_size
        self.ttl = timedelta(minutes=ttl_minutes)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, datetime] = {}
        self._access_counts: Dict[str, int] = {}

        logger.info("Trace cache initialized", extra={
            "max_size": max_size,
            "ttl_minutes": ttl_minutes
        })

    def _evict_if_needed(self):
        """Evict least recently used entry if cache is full."""
        if len(self._cache) >= self.max_size:
            # Find LRU entry
            lru_key = min(self._access_times.items(), key=lambda x: x[1])[0]
            self._evict(lru_key)

    def _evict(self, key: str):
        """Evict a specific cache entry."""
        if key in self._cache:
            del self._cache[key]
            del self._access_times[key]
            del self._access_counts[key]
            logger.debug("Cache entry evicted", extra={"trace_id": key})

    def _is_expired(self, key: str) -> bool:
        """Check if a cache entry has expired."""
        if key not in self._access_times:
            return True

        age = datetime.now() - self._access_times[key]
        return age > self.ttl

    def get(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve trace from cache.

        Args:
            trace_id: Trace identifier

        Returns:
            Cached trace data or None if not found/expired
        """
        # Check if expired
        if self._is_expired(trace_id):
            if trace_id in self._cache:
                self._evict(trace_id)
            return None

        # Check if exists
        if trace_id not in self._cache:
            logger.debug("Cache miss", extra={"trace_id": trace_id})
            return None

        # Update access time and count
        self._access_times[trace_id] = datetime.now()
        self._access_counts[trace_id] += 1

        logger.debug("Cache hit", extra={
            "trace_id": trace_id,
            "access_count": self._access_counts[trace_id]
        })

        return self._cache[trace_id]

    def put(self, trace_id: str, trace_data: Dict[str, Any]):
        """
        Store trace in cache.

        Args:
            trace_id: Trace identifier
            trace_data: Trace data to cache
        """
        # Evict if needed
        self._evict_if_needed()

        # Store in cache
        self._cache[trace_id] = trace_data
        self._access_times[trace_id] = datetime.now()
        self._access_counts[trace_id] = 1

        logger.debug("Trace cached", extra={
            "trace_id": trace_id,
            "cache_size": len(self._cache)
        })

    def invalidate(self, trace_id: str):
        """
        Remove trace from cache.

        Args:
            trace_id: Trace identifier to invalidate
        """
        if trace_id in self._cache:
            self._evict(trace_id)
            logger.debug("Cache invalidated", extra={"trace_id": trace_id})

    def clear(self):
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        self._access_times.clear()
        self._access_counts.clear()
        logger.info("Cache cleared", extra={"entries_cleared": count})

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache metrics
        """
        total_accesses = sum(self._access_counts.values())

        # Get hot traces (most accessed)
        hot_traces = sorted(
            self._access_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "utilization": len(self._cache) / self.max_size if self.max_size > 0 else 0,
            "total_accesses": total_accesses,
            "hot_traces": [
                {"trace_id": trace_id, "access_count": count}
                for trace_id, count in hot_traces
            ],
            "ttl_minutes": self.ttl.total_seconds() / 60
        }


class AnalysisCache:
    """
    Cache for expensive analysis computations.

    Caches results of:
    - Decision analysis (choice probabilities)
    - Attention pattern rankings
    - Token influence calculations
    """

    def __init__(self, max_size: int = 200):
        """
        Initialize analysis cache.

        Args:
            max_size: Maximum number of analysis results to cache
        """
        self.max_size = max_size
        self._cache: Dict[str, Any] = {}
        self._access_times: Dict[str, datetime] = {}

        logger.info("Analysis cache initialized", extra={"max_size": max_size})

    def _make_key(self, operation: str, **params) -> str:
        """
        Generate cache key from operation and parameters.

        Args:
            operation: Type of analysis (e.g., "decision_analysis", "attention_ranking")
            **params: Parameters used in the analysis

        Returns:
            Hash-based cache key
        """
        # Sort parameters for consistent hashing
        sorted_params = json.dumps(params, sort_keys=True)
        key_string = f"{operation}:{sorted_params}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def _evict_if_needed(self):
        """Evict LRU entry if cache is full."""
        if len(self._cache) >= self.max_size:
            lru_key = min(self._access_times.items(), key=lambda x: x[1])[0]
            del self._cache[lru_key]
            del self._access_times[lru_key]
            logger.debug("Analysis cache entry evicted", extra={"key": lru_key})

    def get(self, operation: str, **params) -> Optional[Any]:
        """
        Retrieve cached analysis result.

        Args:
            operation: Type of analysis
            **params: Analysis parameters

        Returns:
            Cached result or None if not found
        """
        key = self._make_key(operation, **params)

        if key not in self._cache:
            logger.debug("Analysis cache miss", extra={
                "operation": operation,
                "key": key
            })
            return None

        # Update access time
        self._access_times[key] = datetime.now()

        logger.debug("Analysis cache hit", extra={
            "operation": operation,
            "key": key
        })

        return self._cache[key]

    def put(self, result: Any, operation: str, **params):
        """
        Store analysis result in cache.

        Args:
            result: Analysis result to cache
            operation: Type of analysis
            **params: Analysis parameters
        """
        key = self._make_key(operation, **params)

        # Evict if needed
        self._evict_if_needed()

        # Store in cache
        self._cache[key] = result
        self._access_times[key] = datetime.now()

        logger.debug("Analysis result cached", extra={
            "operation": operation,
            "key": key,
            "cache_size": len(self._cache)
        })

    def clear(self):
        """Clear all cached analysis results."""
        count = len(self._cache)
        self._cache.clear()
        self._access_times.clear()
        logger.info("Analysis cache cleared", extra={"entries_cleared": count})

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "utilization": len(self._cache) / self.max_size if self.max_size > 0 else 0
        }


# Global cache instances
_trace_cache: Optional[TraceCache] = None
_analysis_cache: Optional[AnalysisCache] = None


def get_trace_cache() -> TraceCache:
    """
    Get global trace cache instance.

    Returns:
        Global TraceCache instance
    """
    global _trace_cache
    if _trace_cache is None:
        _trace_cache = TraceCache()
    return _trace_cache


def get_analysis_cache() -> AnalysisCache:
    """
    Get global analysis cache instance.

    Returns:
        Global AnalysisCache instance
    """
    global _analysis_cache
    if _analysis_cache is None:
        _analysis_cache = AnalysisCache()
    return _analysis_cache


# Example usage and testing
if __name__ == "__main__":
    print("🧠 GlassBox Cache Example\n")
    print("=" * 60)

    # Test trace cache
    print("\n1. Testing TraceCache...")
    cache = TraceCache(max_size=3, ttl_minutes=5)

    # Add some traces
    for i in range(5):
        trace_id = f"20251120_{i:06d}_abc123"
        trace_data = {
            "trace_id": trace_id,
            "prompt": f"Test prompt {i}",
            "output": f"Test output {i}"
        }
        cache.put(trace_id, trace_data)
        print(f"   Cached: {trace_id}")

    # Should have evicted first 2 due to max_size=3
    print(f"\n   Cache size: {len(cache._cache)} (max: 3)")

    # Test cache hit
    hit = cache.get("20251120_000003_abc123")
    print(f"   Cache hit: {hit is not None}")

    # Test cache miss
    miss = cache.get("20251120_000000_abc123")
    print(f"   Cache miss (evicted): {miss is None}")

    # Get stats
    stats = cache.get_stats()
    print(f"\n   Cache stats:")
    print(f"     Size: {stats['size']}/{stats['max_size']}")
    print(f"     Utilization: {stats['utilization']*100:.1f}%")
    print(f"     Total accesses: {stats['total_accesses']}")

    # Test analysis cache
    print("\n2. Testing AnalysisCache...")
    analysis_cache = AnalysisCache(max_size=5)

    # Cache some analysis results
    for i in range(3):
        result = {"choice_probs": {"yes": 0.6, "no": 0.4}}
        analysis_cache.put(
            result,
            operation="decision_analysis",
            prompt=f"Test prompt {i}",
            choices=["yes", "no"]
        )
        print(f"   Cached analysis result {i}")

    # Test cache hit
    cached = analysis_cache.get(
        operation="decision_analysis",
        prompt="Test prompt 1",
        choices=["yes", "no"]
    )
    print(f"   Cache hit: {cached is not None}")

    # Test cache miss (different params)
    cached = analysis_cache.get(
        operation="decision_analysis",
        prompt="Different prompt",
        choices=["yes", "no"]
    )
    print(f"   Cache miss (different params): {cached is None}")

    # Get stats
    stats = analysis_cache.get_stats()
    print(f"\n   Analysis cache stats:")
    print(f"     Size: {stats['size']}/{stats['max_size']}")
    print(f"     Utilization: {stats['utilization']*100:.1f}%")

    print("\n" + "=" * 60)
    print("✅ Cache test complete!\n")
