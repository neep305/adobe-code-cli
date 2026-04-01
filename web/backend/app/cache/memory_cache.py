"""In-memory cache implementation for standalone mode."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional

from cachetools import TTLCache


class MemoryCache:
    """Simple in-memory TTL cache for standalone mode.
    
    This replaces Redis for basic caching functionality when running
    in standalone mode without Docker dependencies.
    """
    
    def __init__(self, maxsize: int = 1000, default_ttl: int = 300):
        """Initialize memory cache.
        
        Args:
            maxsize: Maximum number of items to store
            default_ttl: Default time-to-live in seconds
        """
        self._cache = TTLCache(maxsize=maxsize, ttl=default_ttl)
        self._lock = asyncio.Lock()
        self._default_ttl = default_ttl
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        async with self._lock:
            return self._cache.get(key)
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        async with self._lock:
            if ttl is not None and ttl != self._default_ttl:
                # For custom TTL, create a new cache entry with expiry time
                # cachetools TTLCache uses per-cache TTL, so we store expiry manually
                expiry = datetime.now() + timedelta(seconds=ttl)
                self._cache[key] = {"value": value, "expiry": expiry}
            else:
                self._cache[key] = value
    
    async def delete(self, key: str) -> None:
        """Delete key from cache.
        
        Args:
            key: Cache key to delete
        """
        async with self._lock:
            self._cache.pop(key, None)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists and not expired
        """
        async with self._lock:
            return key in self._cache
    
    async def clear(self) -> None:
        """Clear all cached items."""
        async with self._lock:
            self._cache.clear()
    
    async def keys(self, pattern: str = "*") -> list[str]:
        """Get all keys matching pattern.
        
        Args:
            pattern: Key pattern (basic glob-style matching)
            
        Returns:
            List of matching keys
        """
        async with self._lock:
            if pattern == "*":
                return list(self._cache.keys())
            
            # Simple pattern matching (only supports * wildcard)
            import fnmatch
            return [key for key in self._cache.keys() if fnmatch.fnmatch(key, pattern)]
    
    def __len__(self) -> int:
        """Get number of items in cache."""
        return len(self._cache)
    
    @property
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)
    
    @property
    def maxsize(self) -> int:
        """Get maximum cache size."""
        return self._cache.maxsize


class DiskCache:
    """Simple disk-based cache using diskcache library.
    
    Alternative to memory cache for persistent caching in standalone mode.
    """
    
    def __init__(self, cache_dir: Optional[str] = None, size_limit: int = 2**30):  # 1GB default
        """Initialize disk cache.
        
        Args:
            cache_dir: Directory for cache storage (default: ~/.adobe/web/cache)
            size_limit: Maximum cache size in bytes
        """
        from pathlib import Path
        import diskcache
        
        if cache_dir is None:
            cache_dir = str(Path.home() / ".adobe" / "web" / "cache")
        
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        self._cache = diskcache.Cache(cache_dir, size_limit=size_limit)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        return self._cache.get(key)
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        if ttl:
            self._cache.set(key, value, expire=ttl)
        else:
            self._cache.set(key, value)
    
    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        self._cache.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        return key in self._cache
    
    async def clear(self) -> None:
        """Clear all cached items."""
        self._cache.clear()
    
    async def keys(self, pattern: str = "*") -> list[str]:
        """Get all keys matching pattern."""
        if pattern == "*":
            return list(self._cache)
        
        import fnmatch
        return [key for key in self._cache if fnmatch.fnmatch(key, pattern)]
    
    def __len__(self) -> int:
        """Get number of items in cache."""
        return len(self._cache)
    
    @property
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)


# Global cache instance (initialized in main.py)
_cache: Optional[MemoryCache | DiskCache] = None


def get_cache() -> MemoryCache | DiskCache:
    """Get global cache instance.
    
    Returns:
        Global cache instance
        
    Raises:
        RuntimeError: If cache not initialized
    """
    if _cache is None:
        raise RuntimeError("Cache not initialized. Call init_cache() first.")
    return _cache


def init_cache(backend: str = "memory", **kwargs) -> MemoryCache | DiskCache:
    """Initialize global cache instance.
    
    Args:
        backend: Cache backend ("memory" or "disk")
        **kwargs: Additional arguments for cache initialization
        
    Returns:
        Initialized cache instance
    """
    global _cache
    
    if backend == "memory":
        _cache = MemoryCache(**kwargs)
    elif backend == "disk":
        _cache = DiskCache(**kwargs)
    else:
        raise ValueError(f"Unknown cache backend: {backend}")
    
    return _cache


async def close_cache() -> None:
    """Close and cleanup cache."""
    global _cache
    
    if _cache is not None:
        if isinstance(_cache, DiskCache):
            _cache._cache.close()
        _cache = None
