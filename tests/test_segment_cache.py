"""Tests for SegmentCache."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from adobe_experience.cache.segment_cache import SegmentCache


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create a temporary cache directory."""
    cache_dir = tmp_path / ".adobe" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


@pytest.fixture
def cache_with_temp_dir(temp_cache_dir):
    """Create a SegmentCache instance with temp directory."""
    with patch("adobe_experience.cache.segment_cache.get_config_dir") as mock_config_dir:
        mock_config_dir.return_value = temp_cache_dir.parent
        cache = SegmentCache(ttl_minutes=60)
        yield cache


def test_cache_initialization(cache_with_temp_dir):
    """Test cache initialization creates directory structure."""
    assert cache_with_temp_dir.cache_dir.exists()
    assert cache_with_temp_dir.ttl == timedelta(minutes=60)


def test_save_and_load_mappings(cache_with_temp_dir):
    """Test saving and loading ID mappings."""
    mappings = {
        1: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        2: "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        3: "c3d4e5f6-a7b8-9012-cdef-123456789012",
    }
    
    cache_with_temp_dir.save_mappings(mappings)
    
    # Verify file was created
    assert cache_with_temp_dir.cache_file.exists()
    
    # Verify we can retrieve by number
    assert cache_with_temp_dir.get_id_by_number(1) == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert cache_with_temp_dir.get_id_by_number(2) == "b2c3d4e5-f6a7-8901-bcde-f12345678901"
    assert cache_with_temp_dir.get_id_by_number(3) == "c3d4e5f6-a7b8-9012-cdef-123456789012"


def test_get_nonexistent_number(cache_with_temp_dir):
    """Test retrieving a number that doesn't exist."""
    mappings = {1: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}
    cache_with_temp_dir.save_mappings(mappings)
    
    assert cache_with_temp_dir.get_id_by_number(5) is None


def test_cache_expiration(cache_with_temp_dir):
    """Test that expired cache returns None."""
    # Create cache with 1 minute TTL
    with patch("adobe_experience.cache.segment_cache.get_config_dir") as mock_config_dir:
        mock_config_dir.return_value = cache_with_temp_dir.cache_dir.parent
        short_cache = SegmentCache(ttl_minutes=1)
        
        mappings = {1: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}
        short_cache.save_mappings(mappings)
        
        # Manually modify timestamp to be expired
        cache_data = json.loads(short_cache.cache_file.read_text())
        expired_time = datetime.now() - timedelta(minutes=2)
        cache_data["timestamp"] = expired_time.isoformat()
        short_cache.cache_file.write_text(json.dumps(cache_data))
        
        # Should return None for expired cache
        assert short_cache.get_id_by_number(1) is None


def test_get_all_mappings(cache_with_temp_dir):
    """Test retrieving all mappings."""
    mappings = {
        1: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        2: "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    }
    cache_with_temp_dir.save_mappings(mappings)
    
    all_mappings = cache_with_temp_dir.get_all_mappings()
    assert all_mappings == mappings


def test_get_all_mappings_expired(cache_with_temp_dir):
    """Test that get_all_mappings returns empty dict for expired cache."""
    with patch("adobe_experience.cache.segment_cache.get_config_dir") as mock_config_dir:
        mock_config_dir.return_value = cache_with_temp_dir.cache_dir.parent
        short_cache = SegmentCache(ttl_minutes=1)
        
        mappings = {1: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}
        short_cache.save_mappings(mappings)
        
        # Manually expire
        cache_data = json.loads(short_cache.cache_file.read_text())
        expired_time = datetime.now() - timedelta(minutes=2)
        cache_data["timestamp"] = expired_time.isoformat()
        short_cache.cache_file.write_text(json.dumps(cache_data))
        
        # Should return empty dict
        assert short_cache.get_all_mappings() == {}


def test_clear_cache(cache_with_temp_dir):
    """Test clearing cache removes file."""
    mappings = {1: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}
    cache_with_temp_dir.save_mappings(mappings)
    assert cache_with_temp_dir.cache_file.exists()
    
    cache_with_temp_dir.clear()
    assert not cache_with_temp_dir.cache_file.exists()


def test_get_cache_info(cache_with_temp_dir):
    """Test cache metadata retrieval."""
    mappings = {
        1: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        2: "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    }
    cache_with_temp_dir.save_mappings(mappings)
    
    info = cache_with_temp_dir.get_cache_info()
    
    assert info["entry_count"] == 2
    assert info["is_expired"] is False
    assert info["ttl_minutes"] == 60
    assert "timestamp" in info
    assert "cache_file" in info


def test_corrupted_cache_file(cache_with_temp_dir):
    """Test that corrupted cache file is handled gracefully."""
    # Write invalid JSON
    cache_with_temp_dir.cache_file.write_text("not valid json{")
    
    # Should return None instead of raising error
    assert cache_with_temp_dir.get_id_by_number(1) is None
    
    # Should be able to save new mappings
    mappings = {1: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}
    cache_with_temp_dir.save_mappings(mappings)
    assert cache_with_temp_dir.get_id_by_number(1) == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


def test_cache_overwrite(cache_with_temp_dir):
    """Test that saving new mappings overwrites old ones."""
    # Save first set
    mappings1 = {1: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}
    cache_with_temp_dir.save_mappings(mappings1)
    assert cache_with_temp_dir.get_id_by_number(1) == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    
    # Save second set
    mappings2 = {1: "b2c3d4e5-f6a7-8901-bcde-f12345678901"}
    cache_with_temp_dir.save_mappings(mappings2)
    assert cache_with_temp_dir.get_id_by_number(1) == "b2c3d4e5-f6a7-8901-bcde-f12345678901"


def test_empty_cache(cache_with_temp_dir):
    """Test behavior with empty cache file."""
    # Don't save anything
    assert cache_with_temp_dir.get_id_by_number(1) is None
    assert cache_with_temp_dir.get_all_mappings() == {}
