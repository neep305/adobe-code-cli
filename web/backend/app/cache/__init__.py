"""Cache module for web backend."""

from app.cache.memory_cache import (
    DiskCache,
    MemoryCache,
    close_cache,
    get_cache,
    init_cache,
)

__all__ = [
    "MemoryCache",
    "DiskCache",
    "get_cache",
    "init_cache",
    "close_cache",
]
