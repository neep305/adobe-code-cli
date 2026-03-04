"""Destination ID cache for number-based selection.

Stores recent destination listings with numbered mappings to enable commands like:
    aep destination get 1
Instead of:
    aep destination get d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from adobe_experience.core.config import get_config_dir


class DestinationCache:
    """Manages cached destination ID mappings for numbered selection."""

    def __init__(self, ttl_minutes: int = 60):
        """Initialize cache with specified TTL.

        Args:
            ttl_minutes: Cache entry time-to-live in minutes (default: 60)
        """
        self.ttl = timedelta(minutes=ttl_minutes)
        self.cache_dir = Path(get_config_dir()) / "cache"
        self.cache_file = self.cache_dir / "recent_destinations.json"
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Create cache directory if it doesn't exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _load_cache(self) -> Dict:
        """Load cache from disk."""
        if not self.cache_file.exists():
            return {"timestamp": datetime.now().isoformat(), "mappings": {}}

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"timestamp": datetime.now().isoformat(), "mappings": {}}

    def _save_cache(self, cache_data: Dict) -> None:
        """Save cache to disk."""
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)

    def _is_expired(self, timestamp_str: str) -> bool:
        """Check if cache timestamp is expired."""
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            return datetime.now() - timestamp > self.ttl
        except (ValueError, TypeError):
            return True

    def save_mappings(self, mappings: Dict[int, str]) -> None:
        """Save number-to-ID mappings.

        Args:
            mappings: Dictionary mapping numbers (1, 2, 3...) to destination IDs
        """
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "mappings": {str(k): v for k, v in mappings.items()},
        }
        self._save_cache(cache_data)

    def get_id_by_number(self, number: int) -> Optional[str]:
        """Retrieve destination ID by number.

        Args:
            number: Number from recent destination list (1-based index)

        Returns:
            Destination ID if found and not expired, None otherwise
        """
        cache_data = self._load_cache()

        if self._is_expired(cache_data.get("timestamp", "")):
            return None

        return cache_data.get("mappings", {}).get(str(number))

    def get_all_mappings(self) -> Dict[int, str]:
        """Get all cached mappings if not expired.

        Returns:
            Dictionary of number -> ID mappings, empty if expired
        """
        cache_data = self._load_cache()

        if self._is_expired(cache_data.get("timestamp", "")):
            return {}

        return {int(k): v for k, v in cache_data.get("mappings", {}).items()}

    def clear(self) -> None:
        """Clear all cached mappings."""
        if self.cache_file.exists():
            self.cache_file.unlink()

    def get_cache_info(self) -> Dict:
        """Get cache metadata for debugging.

        Returns:
            Dictionary with timestamp, entry count, and expiration status
        """
        cache_data = self._load_cache()
        timestamp_str = cache_data.get("timestamp", "")
        is_expired = self._is_expired(timestamp_str)

        return {
            "timestamp": timestamp_str,
            "entry_count": len(cache_data.get("mappings", {})),
            "is_expired": is_expired,
            "ttl_minutes": self.ttl.total_seconds() / 60,
            "cache_file": str(self.cache_file),
        }
