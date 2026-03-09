"""Tests for ID Resolver."""

from unittest.mock import Mock, patch

import pytest

from adobe_experience.cli._id_resolver import (
    IDResolver,
    resolve_dataflow_id,
    resolve_dataflow_id_or_fail,
)


@pytest.fixture
def mock_cache():
    """Create a mock DataflowCache."""
    cache = Mock()
    cache.get_id_by_number = Mock(
        side_effect=lambda n: {
            1: "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a",
            2: "a1b2c3d4-e5f6-4a5b-9c8d-7e6f5a4b3c2d",
            3: "f9e8d7c6-b5a4-4321-8765-fedcba987654",
        }.get(n)
    )
    return cache


@pytest.fixture
def resolver(mock_cache):
    """Create an IDResolver with mock cache."""
    return IDResolver(cache=mock_cache)


def test_is_uuid_valid(resolver):
    """Test UUID validation with valid UUIDs."""
    assert resolver.is_uuid("d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a") is True
    assert resolver.is_uuid("A1B2C3D4-E5F6-4A5B-9C8D-7E6F5A4B3C2D") is True  # Uppercase
    assert resolver.is_uuid("f9e8d7c6-b5a4-4321-8765-fedcba987654") is True


def test_is_uuid_invalid(resolver):
    """Test UUID validation with invalid inputs."""
    assert resolver.is_uuid("not-a-uuid") is False
    assert resolver.is_uuid("123") is False
    assert resolver.is_uuid("d8a68c9e-1d5f-4b6c-8a4e") is False  # Too short
    assert resolver.is_uuid("d8a68c9e1d5f4b6c8a4e9f8c7d6e5f4a") is False  # No dashes
    assert resolver.is_uuid("") is False


def test_is_number_valid(resolver):
    """Test number validation with valid numbers."""
    assert resolver.is_number("1") is True
    assert resolver.is_number("42") is True
    assert resolver.is_number("999") is True


def test_is_number_invalid(resolver):
    """Test number validation with invalid inputs."""
    assert resolver.is_number("0") is False  # Zero not allowed
    assert resolver.is_number("-1") is False  # Negative not allowed
    assert resolver.is_number("abc") is False
    assert resolver.is_number("1.5") is False  # Float not allowed
    assert resolver.is_number("") is False


def test_resolve_full_uuid(resolver):
    """Test resolving a full UUID returns it unchanged."""
    uuid = "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a"
    assert resolver.resolve_dataflow_id(uuid) == uuid


def test_resolve_number_from_cache(resolver):
    """Test resolving a number retrieves from cache."""
    assert resolver.resolve_dataflow_id("1") == "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a"
    assert resolver.resolve_dataflow_id("2") == "a1b2c3d4-e5f6-4a5b-9c8d-7e6f5a4b3c2d"
    assert resolver.resolve_dataflow_id("3") == "f9e8d7c6-b5a4-4321-8765-fedcba987654"


def test_resolve_number_not_in_cache(resolver):
    """Test resolving a number not in cache returns None."""
    assert resolver.resolve_dataflow_id("99") is None


def test_resolve_invalid_input(resolver):
    """Test resolving invalid input returns None."""
    assert resolver.resolve_dataflow_id("not-a-uuid-or-number") is None
    assert resolver.resolve_dataflow_id("abc123") is None


def test_resolve_or_fail_success_with_uuid(resolver):
    """Test resolve_or_fail with valid UUID."""
    uuid = "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a"
    assert resolver.resolve_or_fail(uuid) == uuid


def test_resolve_or_fail_success_with_number(resolver):
    """Test resolve_or_fail with valid number."""
    result = resolver.resolve_or_fail("1")
    assert result == "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a"


def test_resolve_or_fail_number_not_found(resolver):
    """Test resolve_or_fail raises error for number not in cache."""
    with pytest.raises(ValueError) as exc_info:
        resolver.resolve_or_fail("99")
    
    assert "Number '99' not found in cache" in str(exc_info.value)
    assert "Run 'aep dataflow list' first" in str(exc_info.value)


def test_resolve_or_fail_invalid_format(resolver):
    """Test resolve_or_fail raises error for invalid format."""
    with pytest.raises(ValueError) as exc_info:
        resolver.resolve_or_fail("not-valid")
    
    assert "Invalid dataflow ID format: 'not-valid'" in str(exc_info.value)
    assert "Expected: number" in str(exc_info.value)


def test_resolve_or_fail_custom_entity_type(resolver):
    """Test resolve_or_fail with custom entity type in error."""
    with pytest.raises(ValueError) as exc_info:
        resolver.resolve_or_fail("invalid", entity_type="connection")
    
    assert "Invalid connection ID format" in str(exc_info.value)


def test_convenience_function_resolve_dataflow_id():
    """Test the convenience function resolve_dataflow_id."""
    with patch("adobe_experience.cli._id_resolver._default_resolver") as mock_resolver:
        mock_resolver.resolve_dataflow_id.return_value = "test-uuid"
        
        result = resolve_dataflow_id("1")
        
        assert result == "test-uuid"
        mock_resolver.resolve_dataflow_id.assert_called_once_with("1")


def test_convenience_function_resolve_dataflow_id_or_fail():
    """Test the convenience function resolve_dataflow_id_or_fail."""
    with patch("adobe_experience.cli._id_resolver._default_resolver") as mock_resolver:
        mock_resolver.resolve_or_fail.return_value = "test-uuid"
        
        result = resolve_dataflow_id_or_fail("1")
        
        assert result == "test-uuid"
        mock_resolver.resolve_or_fail.assert_called_once_with("1", "dataflow")


def test_uuid_case_insensitive(resolver):
    """Test that UUID matching is case-insensitive."""
    assert resolver.is_uuid("D8A68C9E-1D5F-4B6C-8A4E-9F8C7D6E5F4A") is True
    assert resolver.is_uuid("d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a") is True
    
    # Both should resolve as UUIDs
    upper_uuid = "D8A68C9E-1D5F-4B6C-8A4E-9F8C7D6E5F4A"
    lower_uuid = "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a"
    
    assert resolver.resolve_dataflow_id(upper_uuid) == upper_uuid
    assert resolver.resolve_dataflow_id(lower_uuid) == lower_uuid


def test_resolver_with_real_cache():
    """Test resolver works with actual DataflowCache instance."""
    from adobe_experience.cache.dataflow_cache import DataflowCache
    
    with patch("adobe_experience.cache.dataflow_cache.get_config_dir") as mock_config_dir:
        import tempfile
        temp_dir = tempfile.mkdtemp()
        mock_config_dir.return_value = temp_dir
        
        cache = DataflowCache()
        cache.save_mappings({
            1: "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a",
            2: "a1b2c3d4-e5f6-4a5b-9c8d-7e6f5a4b3c2d",
        })
        
        resolver = IDResolver(cache=cache)
        
        assert resolver.resolve_dataflow_id("1") == "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a"
        assert resolver.resolve_dataflow_id("2") == "a1b2c3d4-e5f6-4a5b-9c8d-7e6f5a4b3c2d"


def test_edge_case_zero(resolver):
    """Test that zero is not treated as a valid number."""
    assert resolver.is_number("0") is False
    assert resolver.resolve_dataflow_id("0") is None


def test_edge_case_large_number(resolver):
    """Test large numbers are handled correctly."""
    assert resolver.is_number("12345678") is True
    # Should try to resolve from cache (and return None since not in cache)
    assert resolver.resolve_dataflow_id("12345678") is None


def test_uuid_with_wrong_format(resolver):
    """Test various malformed UUIDs are rejected."""
    assert resolver.is_uuid("d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4") is False  # Too short
    assert resolver.is_uuid("d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4aX") is False  # Too long
    assert resolver.is_uuid("d8a68c9e_1d5f_4b6c_8a4e_9f8c7d6e5f4a") is False  # Wrong separator
    assert resolver.is_uuid("g8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a") is False  # Invalid hex char


# ============================================================================
# SegmentIDResolver Tests
# ============================================================================


@pytest.fixture
def segment_resolver(tmp_path):
    """Create SegmentIDResolver with temp cache."""
    from adobe_experience.cache.segment_cache import SegmentCache
    from adobe_experience.cli._id_resolver import SegmentIDResolver
    
    with patch("adobe_experience.cache.segment_cache.get_config_dir") as mock_config_dir:
        mock_config_dir.return_value = tmp_path
        cache = SegmentCache()
        resolver = SegmentIDResolver(cache)
        yield resolver


def test_segment_is_uuid_valid(segment_resolver):
    """Test UUID validation for segments."""
    assert segment_resolver.is_uuid("a1b2c3d4-e5f6-7890-abcd-ef1234567890") is True
    assert segment_resolver.is_uuid("A1B2C3D4-E5F6-7890-ABCD-EF1234567890") is True  # Case insensitive


def test_segment_is_uuid_invalid(segment_resolver):
    """Test UUID validation rejects invalid formats."""
    assert segment_resolver.is_uuid("not-a-uuid") is False
    assert segment_resolver.is_uuid("123") is False
    assert segment_resolver.is_uuid("") is False
    assert segment_resolver.is_uuid("a1b2c3d4-e5f6-7890-abcd") is False  # Too short


def test_segment_is_number_valid(segment_resolver):
    """Test number validation for segments."""
    assert segment_resolver.is_number("1") is True
    assert segment_resolver.is_number("42") is True
    assert segment_resolver.is_number("999") is True


def test_segment_is_number_invalid(segment_resolver):
    """Test number validation rejects invalid inputs."""
    assert segment_resolver.is_number("0") is False  # Zero not allowed
    assert segment_resolver.is_number("-1") is False  # Negative not allowed
    assert segment_resolver.is_number("abc") is False
    assert segment_resolver.is_number("1.5") is False
    assert segment_resolver.is_number("") is False


def test_segment_resolve_full_uuid(segment_resolver):
    """Test resolving a full UUID passes through."""
    uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert segment_resolver.resolve_segment_id(uuid) == uuid


def test_segment_resolve_number_from_cache(segment_resolver):
    """Test resolving a number from cache."""
    # Populate cache
    mappings = {
        1: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        2: "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    }
    segment_resolver.cache.save_mappings(mappings)
    
    # Resolve numbers
    assert segment_resolver.resolve_segment_id("1") == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert segment_resolver.resolve_segment_id("2") == "b2c3d4e5-f6a7-8901-bcde-f12345678901"


def test_segment_resolve_number_not_in_cache(segment_resolver):
    """Test resolving a number that's not in cache returns None."""
    assert segment_resolver.resolve_segment_id("1") is None
    assert segment_resolver.resolve_segment_id("999") is None


def test_segment_resolve_invalid_format(segment_resolver):
    """Test resolving invalid format returns None."""
    assert segment_resolver.resolve_segment_id("not-a-uuid") is None
    assert segment_resolver.resolve_segment_id("segment-name") is None


def test_segment_resolve_or_fail_success_uuid(segment_resolver):
    """Test resolve_or_fail with valid UUID."""
    uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert segment_resolver.resolve_or_fail(uuid) == uuid


def test_segment_resolve_or_fail_success_number(segment_resolver):
    """Test resolve_or_fail with valid number in cache."""
    mappings = {1: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}
    segment_resolver.cache.save_mappings(mappings)
    
    assert segment_resolver.resolve_or_fail("1") == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


def test_segment_resolve_or_fail_number_not_cached(segment_resolver):
    """Test resolve_or_fail raises error for uncached number."""
    with pytest.raises(ValueError) as exc:
        segment_resolver.resolve_or_fail("1")
    
    assert "Number '1' not found in cache" in str(exc.value)
    assert "aep segment list" in str(exc.value)


def test_segment_resolve_or_fail_invalid_format(segment_resolver):
    """Test resolve_or_fail raises error for invalid format."""
    with pytest.raises(ValueError) as exc:
        segment_resolver.resolve_or_fail("not-a-uuid")
    
    assert "Invalid segment ID format" in str(exc.value)
    assert "not-a-uuid" in str(exc.value)


def test_segment_convenience_function_resolve_id():
    """Test convenience function resolve_segment_id."""
    from adobe_experience.cli._id_resolver import resolve_segment_id
    
    uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert resolve_segment_id(uuid) == uuid


def test_segment_convenience_function_resolve_or_fail():
    """Test convenience function resolve_segment_id_or_fail."""
    from adobe_experience.cli._id_resolver import resolve_segment_id_or_fail
    
    uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert resolve_segment_id_or_fail(uuid) == uuid
    
    # Test failure case
    with pytest.raises(ValueError):
        resolve_segment_id_or_fail("invalid")


# =============================================================================
# DestinationIDResolver Tests
# =============================================================================


@pytest.fixture
def destination_resolver(tmp_path):
    """Create a DestinationIDResolver with temp cache."""
    from adobe_experience.cache.destination_cache import DestinationCache
    from adobe_experience.cli._id_resolver import DestinationIDResolver
    
    with patch("adobe_experience.cache.destination_cache.get_config_dir") as mock_config_dir:
        mock_config_dir.return_value = tmp_path
        cache = DestinationCache()
        resolver = DestinationIDResolver(cache=cache)
        yield resolver


def test_destination_is_uuid_valid(destination_resolver):
    """Test UUID validation for destinations."""
    assert destination_resolver.is_uuid("f1e2d3c4-b5a6-7890-cdef-1234567890ab") is True
    assert destination_resolver.is_uuid("F1E2D3C4-B5A6-7890-CDEF-1234567890AB") is True  # Uppercase


def test_destination_is_uuid_invalid(destination_resolver):
    """Test UUID validation rejects invalid formats."""
    assert destination_resolver.is_uuid("not-a-uuid") is False
    assert destination_resolver.is_uuid("123") is False
    assert destination_resolver.is_uuid("") is False
    assert destination_resolver.is_uuid("f1e2d3c4-b5a6-7890-cdef") is False  # Too short


def test_destination_is_number_valid(destination_resolver):
    """Test number validation for destinations."""
    assert destination_resolver.is_number("1") is True
    assert destination_resolver.is_number("42") is True
    assert destination_resolver.is_number("999") is True


def test_destination_is_number_invalid(destination_resolver):
    """Test number validation rejects invalid inputs."""
    assert destination_resolver.is_number("0") is False  # Zero not allowed
    assert destination_resolver.is_number("-1") is False  # Negative not allowed
    assert destination_resolver.is_number("abc") is False
    assert destination_resolver.is_number("1.5") is False
    assert destination_resolver.is_number("") is False


def test_destination_resolve_full_uuid(destination_resolver):
    """Test resolving a full UUID passes through."""
    uuid = "f1e2d3c4-b5a6-7890-cdef-1234567890ab"
    assert destination_resolver.resolve_destination_id(uuid) == uuid


def test_destination_resolve_number_from_cache(destination_resolver):
    """Test resolving a number from cache."""
    # Populate cache
    mappings = {
        1: "f1e2d3c4-b5a6-7890-cdef-1234567890ab",
        2: "g2f3e4d5-c6b7-8901-defa-bcdef1234567",
    }
    destination_resolver.cache.save_mappings(mappings)
    
    # Resolve numbers
    assert destination_resolver.resolve_destination_id("1") == "f1e2d3c4-b5a6-7890-cdef-1234567890ab"
    assert destination_resolver.resolve_destination_id("2") == "g2f3e4d5-c6b7-8901-defa-bcdef1234567"


def test_destination_resolve_number_not_in_cache(destination_resolver):
    """Test resolving a number that's not in cache returns None."""
    assert destination_resolver.resolve_destination_id("1") is None
    assert destination_resolver.resolve_destination_id("999") is None


def test_destination_resolve_invalid_format(destination_resolver):
    """Test resolving invalid format returns None."""
    assert destination_resolver.resolve_destination_id("not-a-uuid") is None
    assert destination_resolver.resolve_destination_id("destination-name") is None


def test_destination_resolve_or_fail_success_uuid(destination_resolver):
    """Test resolve_or_fail with valid UUID."""
    uuid = "f1e2d3c4-b5a6-7890-cdef-1234567890ab"
    assert destination_resolver.resolve_or_fail(uuid) == uuid


def test_destination_resolve_or_fail_success_number(destination_resolver):
    """Test resolve_or_fail with valid number in cache."""
    mappings = {1: "f1e2d3c4-b5a6-7890-cdef-1234567890ab"}
    destination_resolver.cache.save_mappings(mappings)
    
    assert destination_resolver.resolve_or_fail("1") == "f1e2d3c4-b5a6-7890-cdef-1234567890ab"


def test_destination_resolve_or_fail_number_not_cached(destination_resolver):
    """Test resolve_or_fail raises error for uncached number."""
    with pytest.raises(ValueError) as exc:
        destination_resolver.resolve_or_fail("1")
    
    assert "Number '1' not found in cache" in str(exc.value)
    assert "aep destination list" in str(exc.value)


def test_destination_resolve_or_fail_invalid_format(destination_resolver):
    """Test resolve_or_fail raises error for invalid format."""
    with pytest.raises(ValueError) as exc:
        destination_resolver.resolve_or_fail("not-a-uuid")
    
    assert "Invalid destination ID format" in str(exc.value)
    assert "not-a-uuid" in str(exc.value)


def test_destination_convenience_function_resolve_id():
    """Test convenience function resolve_destination_id."""
    from adobe_experience.cli._id_resolver import resolve_destination_id
    
    uuid = "f1e2d3c4-b5a6-7890-cdef-1234567890ab"
    assert resolve_destination_id(uuid) == uuid


def test_destination_convenience_function_resolve_or_fail():
    """Test convenience function resolve_destination_id_or_fail."""
    from adobe_experience.cli._id_resolver import resolve_destination_id_or_fail
    
    uuid = "f1e2d3c4-b5a6-7890-cdef-1234567890ab"
    assert resolve_destination_id_or_fail(uuid) == uuid
    
    # Test failure case
    with pytest.raises(ValueError):
        resolve_destination_id_or_fail("invalid")
