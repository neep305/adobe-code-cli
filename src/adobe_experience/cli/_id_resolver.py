"""ID resolver utility for CLI commands.

Resolves various ID input formats:
- Numbers (1, 2, 3) -> Full UUID from cache
- Full UUIDs -> Pass through
- Names -> Search by name (future enhancement)
"""

import re
from typing import Optional

from adobe_experience.cache.dataflow_cache import DataflowCache
from adobe_experience.cache.destination_cache import DestinationCache
from adobe_experience.cache.segment_cache import SegmentCache


class IDResolver:
    """Resolves different ID input formats to full UUIDs."""

    # UUID pattern: 8-4-4-4-12 hex characters
    UUID_PATTERN = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        re.IGNORECASE,
    )

    def __init__(self, cache: Optional[DataflowCache] = None):
        """Initialize resolver with optional cache instance.

        Args:
            cache: DataflowCache instance (creates new if not provided)
        """
        self.cache = cache or DataflowCache()

    def is_uuid(self, value: str) -> bool:
        """Check if value is a valid UUID format.

        Args:
            value: String to check

        Returns:
            True if value matches UUID pattern
        """
        return bool(self.UUID_PATTERN.match(value))

    def is_number(self, value: str) -> bool:
        """Check if value is a positive integer.

        Args:
            value: String to check

        Returns:
            True if value is a positive integer
        """
        return value.isdigit() and int(value) > 0

    def resolve_dataflow_id(self, id_input: str) -> Optional[str]:
        """Resolve dataflow ID from various input formats.

        Args:
            id_input: Input string (number, UUID, or name)

        Returns:
            Full UUID if resolved, None if not found

        Examples:
            >>> resolver.resolve_dataflow_id("1")  # Number from cache
            "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a"

            >>> resolver.resolve_dataflow_id("d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a")  # UUID
            "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a"
        """
        # Case 1: Full UUID - pass through
        if self.is_uuid(id_input):
            return id_input

        # Case 2: Number - lookup in cache
        if self.is_number(id_input):
            number = int(id_input)
            resolved_id = self.cache.get_id_by_number(number)
            return resolved_id

        # Case 3: Name search (future enhancement)
        # For now, return None for non-UUID, non-number inputs
        return None

    def resolve_or_fail(self, id_input: str, entity_type: str = "dataflow") -> str:
        """Resolve ID or raise descriptive error.

        Args:
            id_input: Input string to resolve
            entity_type: Type of entity for error messages

        Returns:
            Resolved UUID

        Raises:
            ValueError: If ID cannot be resolved
        """
        resolved = self.resolve_dataflow_id(id_input)

        if resolved is None:
            if self.is_number(id_input):
                raise ValueError(
                    f"Number '{id_input}' not found in cache. "
                    f"Run 'aep dataflow list' first to populate the cache, "
                    f"or provide the full {entity_type} ID."
                )
            else:
                raise ValueError(
                    f"Invalid {entity_type} ID format: '{id_input}'. "
                    f"Expected: number (1, 2, 3...) or full UUID "
                    f"(xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)"
                )

        return resolved


# Singleton instance for convenience
_default_resolver = IDResolver()


def resolve_dataflow_id(id_input: str) -> Optional[str]:
    """Convenience function to resolve dataflow ID.

    Args:
        id_input: Input string (number, UUID, or name)

    Returns:
        Resolved UUID or None
    """
    return _default_resolver.resolve_dataflow_id(id_input)


def resolve_dataflow_id_or_fail(id_input: str) -> str:
    """Convenience function to resolve dataflow ID or raise error.

    Args:
        id_input: Input string to resolve

    Returns:
        Resolved UUID

    Raises:
        ValueError: If ID cannot be resolved
    """
    return _default_resolver.resolve_or_fail(id_input, "dataflow")


class SegmentIDResolver:
    """Resolves different segment ID input formats to full UUIDs."""

    # UUID pattern: 8-4-4-4-12 hex characters
    UUID_PATTERN = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        re.IGNORECASE,
    )

    def __init__(self, cache: Optional[SegmentCache] = None):
        """Initialize resolver with optional cache instance.

        Args:
            cache: SegmentCache instance (creates new if not provided)
        """
        self.cache = cache or SegmentCache()

    def is_uuid(self, value: str) -> bool:
        """Check if value is a valid UUID format.

        Args:
            value: String to check

        Returns:
            True if value matches UUID pattern
        """
        return bool(self.UUID_PATTERN.match(value))

    def is_number(self, value: str) -> bool:
        """Check if value is a positive integer.

        Args:
            value: String to check

        Returns:
            True if value is a positive integer
        """
        return value.isdigit() and int(value) > 0

    def resolve_segment_id(self, id_input: str) -> Optional[str]:
        """Resolve segment ID from various input formats.

        Args:
            id_input: Input string (number, UUID, or name)

        Returns:
            Full UUID if resolved, None if not found

        Examples:
            >>> resolver.resolve_segment_id("1")  # Number from cache
            "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

            >>> resolver.resolve_segment_id("a1b2c3d4-e5f6-7890-abcd-ef1234567890")  # UUID
            "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        """
        # Case 1: Full UUID - pass through
        if self.is_uuid(id_input):
            return id_input

        # Case 2: Number - lookup in cache
        if self.is_number(id_input):
            number = int(id_input)
            resolved_id = self.cache.get_id_by_number(number)
            return resolved_id

        # Case 3: Name search (future enhancement)
        # For now, return None for non-UUID, non-number inputs
        return None

    def resolve_or_fail(self, id_input: str, entity_type: str = "segment") -> str:
        """Resolve ID or raise descriptive error.

        Args:
            id_input: Input string to resolve
            entity_type: Type of entity for error messages

        Returns:
            Resolved UUID

        Raises:
            ValueError: If ID cannot be resolved
        """
        resolved = self.resolve_segment_id(id_input)

        if resolved is None:
            if self.is_number(id_input):
                raise ValueError(
                    f"Number '{id_input}' not found in cache. "
                    f"Run 'aep segment list' first to populate the cache, "
                    f"or provide the full {entity_type} ID."
                )
            else:
                raise ValueError(
                    f"Invalid {entity_type} ID format: '{id_input}'. "
                    f"Expected: number (1, 2, 3...) or full UUID "
                    f"(xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)"
                )

        return resolved


# Singleton instance for segment resolution
_default_segment_resolver = SegmentIDResolver()


def resolve_segment_id(id_input: str) -> Optional[str]:
    """Convenience function to resolve segment ID.

    Args:
        id_input: Input string (number, UUID, or name)

    Returns:
        Resolved UUID or None
    """
    return _default_segment_resolver.resolve_segment_id(id_input)


def resolve_segment_id_or_fail(id_input: str) -> str:
    """Convenience function to resolve segment ID or raise error.

    Args:
        id_input: Input string to resolve

    Returns:
        Resolved UUID

    Raises:
        ValueError: If ID cannot be resolved
    """
    return _default_segment_resolver.resolve_or_fail(id_input, "segment")


class DestinationIDResolver:
    """Resolves different destination ID input formats to full UUIDs."""

    # UUID pattern: 8-4-4-4-12 hex characters
    UUID_PATTERN = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        re.IGNORECASE,
    )

    def __init__(self, cache: Optional[DestinationCache] = None):
        """Initialize resolver with optional cache instance.

        Args:
            cache: DestinationCache instance (creates new if not provided)
        """
        self.cache = cache or DestinationCache()

    def is_uuid(self, value: str) -> bool:
        """Check if value is a valid UUID format.

        Args:
            value: String to check

        Returns:
            True if value matches UUID pattern
        """
        return bool(self.UUID_PATTERN.match(value))

    def is_number(self, value: str) -> bool:
        """Check if value is a positive integer.

        Args:
            value: String to check

        Returns:
            True if value is a positive integer
        """
        return value.isdigit() and int(value) > 0

    def resolve_destination_id(self, id_input: str) -> Optional[str]:
        """Resolve destination ID from various input formats.

        Args:
            id_input: Input string (number, UUID, or name)

        Returns:
            Full UUID if resolved, None if not found

        Examples:
            >>> resolver.resolve_destination_id("1")  # Number from cache
            "f1e2d3c4-b5a6-7890-cdef-1234567890ab"

            >>> resolver.resolve_destination_id("f1e2d3c4-b5a6-7890-cdef-1234567890ab")  # UUID
            "f1e2d3c4-b5a6-7890-cdef-1234567890ab"
        """
        # Case 1: Full UUID - pass through
        if self.is_uuid(id_input):
            return id_input

        # Case 2: Number - lookup in cache
        if self.is_number(id_input):
            number = int(id_input)
            resolved_id = self.cache.get_id_by_number(number)
            return resolved_id

        # Case 3: Name search (future enhancement)
        # For now, return None for non-UUID, non-number inputs
        return None

    def resolve_or_fail(self, id_input: str, entity_type: str = "destination") -> str:
        """Resolve ID or raise descriptive error.

        Args:
            id_input: Input string to resolve
            entity_type: Type of entity for error messages

        Returns:
            Resolved UUID

        Raises:
            ValueError: If ID cannot be resolved
        """
        resolved = self.resolve_destination_id(id_input)

        if resolved is None:
            if self.is_number(id_input):
                raise ValueError(
                    f"Number '{id_input}' not found in cache. "
                    f"Run 'aep destination list' first to populate the cache, "
                    f"or provide the full {entity_type} ID."
                )
            else:
                raise ValueError(
                    f"Invalid {entity_type} ID format: '{id_input}'. "
                    f"Expected: number (1, 2, 3...) or full UUID "
                    f"(xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)"
                )

        return resolved


# Singleton instance for destination resolution
_default_destination_resolver = DestinationIDResolver()


def resolve_destination_id(id_input: str) -> Optional[str]:
    """Convenience function to resolve destination ID.

    Args:
        id_input: Input string (number, UUID, or name)

    Returns:
        Resolved UUID or None
    """
    return _default_destination_resolver.resolve_destination_id(id_input)


def resolve_destination_id_or_fail(id_input: str) -> str:
    """Convenience function to resolve destination ID or raise error.

    Args:
        id_input: Input string to resolve

    Returns:
        Resolved UUID

    Raises:
        ValueError: If ID cannot be resolved
    """
    return _default_destination_resolver.resolve_or_fail(id_input, "destination")
