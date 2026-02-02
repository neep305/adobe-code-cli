"""Unit tests for bulk file upload client."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from adobe_experience.ingestion.bulk_upload import BulkIngestClient


@pytest.fixture
def mock_aep_client():
    """Mock AEPClient for testing."""
    client = AsyncMock()
    client.config = MagicMock()
    return client


@pytest.fixture
def temp_test_file(tmp_path):
    """Create a temporary test file."""
    test_file = tmp_path / "test_data.json"
    test_file.write_text('{"id": 1, "name": "test"}')
    return test_file


@pytest.fixture
def temp_test_files(tmp_path):
    """Create multiple temporary test files."""
    files = []
    for i in range(3):
        test_file = tmp_path / f"test_data_{i}.json"
        test_file.write_text(f'{{"id": {i}, "name": "test{i}"}}')
        files.append(test_file)
    return files


# ==================== Single File Upload Tests ====================


@pytest.mark.asyncio
async def test_upload_file_success(mock_aep_client, temp_test_file):
    """Test successful file upload."""
    mock_aep_client.put.return_value = {}
    
    bulk = BulkIngestClient(mock_aep_client)
    result = await bulk.upload_file(
        batch_id="batch123",
        dataset_id="dataset456",
        file_path=temp_test_file
    )
    
    assert result["file_name"] == "test_data.json"
    assert result["size_bytes"] > 0
    assert result["status"] == "uploaded"
    assert "content_type" in result
    
    mock_aep_client.put.assert_called_once()
    call_args = mock_aep_client.put.call_args
    assert "/batches/batch123/datasets/dataset456/files/test_data.json" in call_args[0][0]


@pytest.mark.asyncio
async def test_upload_file_with_custom_name(mock_aep_client, temp_test_file):
    """Test file upload with custom name."""
    mock_aep_client.put.return_value = {}
    
    bulk = BulkIngestClient(mock_aep_client)
    result = await bulk.upload_file(
        batch_id="batch123",
        dataset_id="dataset456",
        file_path=temp_test_file,
        file_name="custom_name.json"
    )
    
    assert result["file_name"] == "custom_name.json"
    call_args = mock_aep_client.put.call_args
    assert "custom_name.json" in call_args[0][0]


@pytest.mark.asyncio
async def test_upload_file_not_found(mock_aep_client):
    """Test upload of non-existent file."""
    bulk = BulkIngestClient(mock_aep_client)
    
    with pytest.raises(FileNotFoundError):
        await bulk.upload_file(
            batch_id="batch123",
            dataset_id="dataset456",
            file_path="nonexistent.json"
        )


@pytest.mark.asyncio
async def test_upload_empty_file(mock_aep_client, tmp_path):
    """Test upload of empty file."""
    empty_file = tmp_path / "empty.json"
    empty_file.write_text("")
    
    bulk = BulkIngestClient(mock_aep_client)
    
    with pytest.raises(ValueError, match="File is empty"):
        await bulk.upload_file(
            batch_id="batch123",
            dataset_id="dataset456",
            file_path=empty_file
        )


@pytest.mark.asyncio
async def test_upload_file_too_large(mock_aep_client, temp_test_file):
    """Test handling of file too large error."""
    import httpx
    
    # Simulate 413 error
    response = MagicMock()
    response.status_code = 413
    error = httpx.HTTPStatusError("File too large", request=MagicMock(), response=response)
    mock_aep_client.put.side_effect = error
    
    bulk = BulkIngestClient(mock_aep_client)
    
    with pytest.raises(ValueError, match="File too large"):
        await bulk.upload_file(
            batch_id="batch123",
            dataset_id="dataset456",
            file_path=temp_test_file
        )


# ==================== Multiple File Upload Tests ====================


@pytest.mark.asyncio
async def test_upload_multiple_files_success(mock_aep_client, temp_test_files):
    """Test uploading multiple files."""
    mock_aep_client.put.return_value = {}
    
    bulk = BulkIngestClient(mock_aep_client)
    results = await bulk.upload_multiple_files(
        batch_id="batch123",
        dataset_id="dataset456",
        file_paths=temp_test_files,
        max_concurrent=2
    )
    
    assert len(results) == 3
    assert all(r["status"] == "uploaded" for r in results)
    assert mock_aep_client.put.call_count == 3


@pytest.mark.asyncio
async def test_upload_multiple_files_with_errors(mock_aep_client, temp_test_files):
    """Test multiple file upload with some failures."""
    # First file succeeds, second fails, third succeeds
    mock_aep_client.put.side_effect = [
        {},
        Exception("Network error"),
        {}
    ]
    
    bulk = BulkIngestClient(mock_aep_client)
    results = await bulk.upload_multiple_files(
        batch_id="batch123",
        dataset_id="dataset456",
        file_paths=temp_test_files,
        max_concurrent=1
    )
    
    assert len(results) == 3
    assert results[0]["status"] == "uploaded"
    assert results[1]["status"] == "failed"
    assert "error" in results[1]
    assert results[2]["status"] == "uploaded"


# ==================== Directory Upload Tests ====================


@pytest.mark.asyncio
async def test_upload_directory_success(mock_aep_client, temp_test_files, tmp_path):
    """Test uploading all files from directory."""
    mock_aep_client.put.return_value = {}
    
    bulk = BulkIngestClient(mock_aep_client)
    results = await bulk.upload_directory(
        batch_id="batch123",
        dataset_id="dataset456",
        directory_path=tmp_path,
        pattern="*.json"
    )
    
    assert len(results) == 3
    assert all(r["status"] == "uploaded" for r in results)


@pytest.mark.asyncio
async def test_upload_directory_with_pattern(mock_aep_client, tmp_path):
    """Test uploading files matching pattern."""
    # Create mixed file types
    (tmp_path / "data1.json").write_text('{"test": 1}')
    (tmp_path / "data2.txt").write_text("test")
    (tmp_path / "data3.json").write_text('{"test": 2}')
    
    mock_aep_client.put.return_value = {}
    
    bulk = BulkIngestClient(mock_aep_client)
    results = await bulk.upload_directory(
        batch_id="batch123",
        dataset_id="dataset456",
        directory_path=tmp_path,
        pattern="*.json"
    )
    
    # Should only upload .json files
    assert len(results) == 2
    assert all("json" in r["file_name"] for r in results)


@pytest.mark.asyncio
async def test_upload_directory_not_found(mock_aep_client):
    """Test upload from non-existent directory."""
    bulk = BulkIngestClient(mock_aep_client)
    
    with pytest.raises(NotADirectoryError):
        await bulk.upload_directory(
            batch_id="batch123",
            dataset_id="dataset456",
            directory_path="nonexistent_dir"
        )


@pytest.mark.asyncio
async def test_upload_directory_no_matching_files(mock_aep_client, tmp_path):
    """Test upload when no files match pattern."""
    (tmp_path / "test.txt").write_text("test")
    
    bulk = BulkIngestClient(mock_aep_client)
    
    with pytest.raises(ValueError, match="No files found"):
        await bulk.upload_directory(
            batch_id="batch123",
            dataset_id="dataset456",
            directory_path=tmp_path,
            pattern="*.json"
        )


@pytest.mark.asyncio
async def test_upload_directory_recursive(mock_aep_client, tmp_path):
    """Test recursive directory upload."""
    # Create nested structure
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (tmp_path / "file1.json").write_text('{"test": 1}')
    (subdir / "file2.json").write_text('{"test": 2}')
    
    mock_aep_client.put.return_value = {}
    
    bulk = BulkIngestClient(mock_aep_client)
    
    # Non-recursive: should find 1 file
    results = await bulk.upload_directory(
        batch_id="batch123",
        dataset_id="dataset456",
        directory_path=tmp_path,
        pattern="*.json",
        recursive=False
    )
    assert len(results) == 1
    
    # Recursive: should find 2 files
    mock_aep_client.put.reset_mock()
    results = await bulk.upload_directory(
        batch_id="batch123",
        dataset_id="dataset456",
        directory_path=tmp_path,
        pattern="*.json",
        recursive=True
    )
    assert len(results) == 2


# ==================== Upload Status Tests ====================


@pytest.mark.asyncio
async def test_get_upload_status_file_exists(mock_aep_client):
    """Test checking upload status for existing file."""
    from adobe_experience.catalog.models import DataSetFile
    
    # Mock catalog service response
    mock_file = DataSetFile(
        id="file123",
        dataSetId="dataset456",
        batchId="batch123",
        name="test_data.json",
        sizeInBytes=1024,
        records=100,
        created=1234567890000,
        isValid=True
    )
    
    with patch("adobe_experience.catalog.client.CatalogServiceClient") as mock_catalog_class:
        mock_catalog_instance = AsyncMock()
        mock_catalog_instance.list_dataset_files = AsyncMock(return_value=[mock_file])
        mock_catalog_class.return_value = mock_catalog_instance
        
        bulk = BulkIngestClient(mock_aep_client)
        status = await bulk.get_upload_status(
            batch_id="batch123",
            file_name="test_data.json"
        )
        
        assert status["exists"] is True
        assert status["file_name"] == "test_data.json"
        assert status["size_bytes"] == 1024
        assert status["records"] == 100
        assert status["is_valid"] is True


@pytest.mark.asyncio
async def test_get_upload_status_file_not_exists(mock_aep_client):
    """Test checking upload status for non-existent file."""
    with patch("adobe_experience.catalog.client.CatalogServiceClient") as mock_catalog_class:
        mock_catalog_instance = AsyncMock()
        mock_catalog_instance.list_dataset_files = AsyncMock(return_value=[])
        mock_catalog_class.return_value = mock_catalog_instance
        
        bulk = BulkIngestClient(mock_aep_client)
        status = await bulk.get_upload_status(
            batch_id="batch123",
            file_name="nonexistent.json"
        )
        
        assert status["exists"] is False
        assert status["file_name"] == "nonexistent.json"


# ==================== Content Type Detection Tests ====================


@pytest.mark.asyncio
async def test_content_type_detection(mock_aep_client, tmp_path):
    """Test automatic content type detection."""
    test_files = [
        ("data.json", "application/json"),
        ("data.parquet", "application/octet-stream"),  # No standard MIME type
        ("data.csv", "text/csv"),
        ("data.txt", "text/plain"),
    ]
    
    mock_aep_client.put.return_value = {}
    
    for filename, expected_type in test_files:
        test_file = tmp_path / filename
        test_file.write_text("test content")
        
        bulk = BulkIngestClient(mock_aep_client)
        result = await bulk.upload_file(
            batch_id="batch123",
            dataset_id="dataset456",
            file_path=test_file
        )
        
        # Check headers in call
        call_args = mock_aep_client.put.call_args
        headers = call_args[1]["headers"]
        assert "Content-Type" in headers
