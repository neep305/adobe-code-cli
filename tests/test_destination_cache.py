"""Tests for DestinationCache."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from adobe_experience.cache.destination_cache import DestinationCache


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create a temporary cache directory."""
    cache_dir = tmp_path / ".adobe" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


@pytest.fixture
def cache_with_temp_dir(temp_cache_dir):
    """Create a DestinationCache instance with temp directory."""
    with patch("adobe_experience.cache.destination_cache.get_config_dir") as mock_config_dir:
        mock_config_dir.return_value = temp_cache_dir.parent
        cache = DestinationCache(ttl_minutes=60)
        yield cache


def test_cache_initialization(cache_with_temp_dir):
    """Test cache initialization creates directory structure."""
    assert cache_with_temp_dir.cache_dir.exists()
    assert cache_with_temp_dir.ttl == timedelta(minutes=60)


def test_save_and_load_mappings(cache_with_temp_dir):
    """Test saving and loading ID mappings."""
    mappings = {
        1: "f1e2d3c4-b5a6-7890-cdef-1234567890ab",
        2: "g2f3e4d5-c6b7-8901-defa-bcdef1234567",
        3: "h3g4f5e6-d7c8-9012-abcd-ef1234567890",
    }
    
    cache_with_temp_dir.save_mappings(mappings)
    
    # Verify file was created
    assert cache_with_temp_dir.cache_file.exists()
    
    # Verify we can retrieve by number
    assert cache_with_temp_dir.get_id_by_number(1) == "f1e2d3c4-b5a6-7890-cdef-1234567890ab"
    assert cache_with_temp_dir.get_id_by_number(2) == "g2f3e4d5-c6b7-8901-defa-bcdef1234567"
    assert cache_with_temp_dir.get_id_by_number(3) == "h3g4f5e6-d7c8-9012-abcd-ef1234567890"


def test_get_nonexistent_number(cache_with_temp_dir):
    """Test retrieving a number that doesn't exist."""
    mappings = {1: "f1e2d3c4-b5a6-7890-cdef-1234567890ab"}
    cache_with_temp_dir.save_mappings(mappings)
    
    assert cache_with_temp_dir.get_id_by_number(5) is None


def test_cache_expiration(cache_with_temp_dir):
    """Test that expired cache returns None."""
    # Create cache with 1 minute TTL
    with patch("adobe_experience.cache.destination_cache.get_config_dir") as mock_config_dir:
        mock_config_dir.return_value = cache_with_temp_dir.cache_dir.parent
        short_cache = DestinationCache(ttl_minutes=1)
        
        mappings = {1: "f1e2d3c4-b5a6-7890-cdef-1234567890ab"}
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
        1: "f1e2d3c4-b5a6-7890-cdef-1234567890ab",
        2: "g2f3e4d5-c6b7-8901-defa-bcdef1234567",
    }
    cache_with_temp_dir.save_mappings(mappings)
    
    all_mappings = cache_with_temp_dir.get_all_mappings()
    assert all_mappings == mappings


def test_get_all_mappings_expired(cache_with_temp_dir):
    """Test that get_all_mappings returns empty dict for expired cache."""
    with patch("adobe_experience.cache.destination_cache.get_config_dir") as mock_config_dir:
        mock_config_dir.return_value = cache_with_temp_dir.cache_dir.parent
        short_cache = DestinationCache(ttl_minutes=1)
        
        mappings = {1: "f1e2d3c4-b5a6-7890-cdef-1234567890ab"}
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
    mappings = {1: "f1e2d3c4-b5a6-7890-cdef-1234567890ab"}
    cache_with_temp_dir.save_mappings(mappings)
    assert cache_with_temp_dir.cache_file.exists()
    
    cache_with_temp_dir.clear()
    assert not cache_with_temp_dir.cache_file.exists()


def test_get_cache_info(cache_with_temp_dir):
    """Test cache metadata retrieval."""
    mappings = {
        1: "f1e2d3c4-b5a6-7890-cdef-1234567890ab",
        2: "g2f3e4d5-c6b7-8901-defa-bcdef1234567",
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
    cache_with_temp_dir.cache_file.write_text("not valid json{{{")
    
    # Should not crash, should return None
    assert cache_with_temp_dir.get_id_by_number(1) is None


def test_empty_cache(cache_with_temp_dir):
    """Test behavior with empty cache."""
    # Don't save any mappings
    assert cache_with_temp_dir.get_id_by_number(1) is None
    assert cache_with_temp_dir.get_all_mappings() == {}


def test_overwrite_existing_cache(cache_with_temp_dir):
    """Test that saving new mappings overwrites old ones."""
    old_mappings = {1: "f1e2d3c4-b5a6-7890-cdef-1234567890ab"}
    cache_with_temp_dir.save_mappings(old_mappings)
    
    new_mappings = {
        1: "g2f3e4d5-c6b7-8901-defa-bcdef1234567",
        2: "h3g4f5e6-d7c8-9012-abcd-ef1234567890",
    }
    cache_with_temp_dir.save_mappings(new_mappings)
    
    # Old mapping should be gone
    assert cache_with_temp_dir.get_id_by_number(1) == "g2f3e4d5-c6b7-8901-defa-bcdef1234567"
    assert cache_with_temp_dir.get_id_by_number(2) == "h3g4f5e6-d7c8-9012-abcd-ef1234567890"
