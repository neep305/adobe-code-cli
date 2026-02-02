"""Integration tests for end-to-end data ingestion workflow.

These tests require:
1. Valid Adobe AEP credentials in environment or config
2. Access to a test sandbox
3. A test dataset with proper schema

Run with: pytest tests/test_ingestion_integration.py -v --integration
"""

import asyncio
from pathlib import Path
from typing import Optional

import pytest

from adobe_experience.aep.client import AEPClient
from adobe_experience.catalog.client import CatalogServiceClient
from adobe_experience.catalog.models import BatchStatus
from adobe_experience.core.config import get_config
from adobe_experience.ingestion.bulk_upload import BulkIngestClient

# Skip integration tests by default (require --integration flag)
pytestmark = pytest.mark.skipif(
    "not config.getoption('--integration', default=False)",
    reason="Integration tests require --integration flag and live AEP sandbox"
)


def pytest_addoption(parser):
    """Add --integration flag to pytest."""
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests against live AEP sandbox"
    )


@pytest.fixture
async def aep_client():
    """Create AEP client from config."""
    try:
        config = get_config()
        client = AEPClient(
            client_id=config.client_id,
            client_secret=config.client_secret,
            org_id=config.org_id,
            sandbox_name=config.sandbox_name,
        )
        yield client
    except Exception as e:
        pytest.skip(f"Could not create AEP client: {e}")


@pytest.fixture
async def catalog_client(aep_client):
    """Create Catalog Service client."""
    return CatalogServiceClient(aep_client)


@pytest.fixture
async def bulk_client(aep_client):
    """Create Bulk Ingest client."""
    return BulkIngestClient(aep_client)


@pytest.fixture
def test_dataset_id() -> Optional[str]:
    """Test dataset ID from environment.
    
    Set TEST_DATASET_ID environment variable to run integration tests.
    """
    import os
    dataset_id = os.getenv("TEST_DATASET_ID")
    if not dataset_id:
        pytest.skip("TEST_DATASET_ID environment variable not set")
    return dataset_id


@pytest.fixture
def temp_test_file(tmp_path: Path) -> Path:
    """Create temporary test JSON file."""
    test_file = tmp_path / "integration_test_data.json"
    test_data = """[
  {
    "id": "test_001",
    "name": "Integration Test Customer",
    "email": "integration@test.com",
    "created_at": "2026-02-02T10:00:00Z"
  },
  {
    "id": "test_002",
    "name": "Integration Test Customer 2",
    "email": "integration2@test.com",
    "created_at": "2026-02-02T10:01:00Z"
  }
]"""
    test_file.write_text(test_data)
    return test_file


@pytest.mark.asyncio
async def test_end_to_end_single_file_upload(
    catalog_client: CatalogServiceClient,
    bulk_client: BulkIngestClient,
    test_dataset_id: str,
    temp_test_file: Path,
):
    """Test complete workflow: create batch → upload file → complete batch → verify.
    
    This is the primary integration test for data ingestion.
    """
    # Step 1: Create batch
    print(f"\n1. Creating batch for dataset {test_dataset_id}...")
    batch = await catalog_client.create_batch(
        dataset_id=test_dataset_id,
        format="json"
    )
    assert batch is not None
    assert batch.id is not None
    print(f"   ✓ Batch created: {batch.id}")
    
    # Step 2: Upload file
    print(f"2. Uploading file {temp_test_file.name}...")
    upload_result = await bulk_client.upload_file(
        file_path=temp_test_file,
        batch_id=batch.id,
        file_name="integration_test.json"
    )
    assert upload_result["success"] is True
    assert upload_result["file_name"] == "integration_test.json"
    print(f"   ✓ File uploaded: {upload_result['size_bytes']} bytes")
    
    # Step 3: Verify file was uploaded
    print("3. Verifying file upload status...")
    status = await bulk_client.get_upload_status(
        batch_id=batch.id,
        file_name="integration_test.json"
    )
    assert status["exists"] is True
    assert status["file_name"] == "integration_test.json"
    print(f"   ✓ File verified in batch")
    
    # Step 4: Complete batch
    print("4. Completing batch...")
    await catalog_client.complete_batch(batch.id)
    print(f"   ✓ Batch marked as complete")
    
    # Step 5: Wait for batch processing
    print("5. Waiting for batch processing (timeout 300s)...")
    try:
        final_batch = await catalog_client.wait_for_batch_completion(
            batch_id=batch.id,
            timeout=300,
            poll_interval=5
        )
        print(f"   ✓ Batch processing complete")
        print(f"   Status: {final_batch.status.value}")
        if final_batch.metrics:
            print(f"   Records read: {final_batch.metrics.recordsRead}")
            print(f"   Records written: {final_batch.metrics.recordsWritten}")
        
        # Verify batch succeeded
        assert final_batch.status in [BatchStatus.SUCCESS, BatchStatus.ACTIVE], \
            f"Batch failed with status: {final_batch.status.value}"
            
    except asyncio.TimeoutError:
        pytest.fail("Batch processing timed out after 300 seconds")


@pytest.mark.asyncio
async def test_end_to_end_multiple_files_upload(
    catalog_client: CatalogServiceClient,
    bulk_client: BulkIngestClient,
    test_dataset_id: str,
    tmp_path: Path,
):
    """Test uploading multiple files to a batch concurrently."""
    # Create multiple test files
    files = []
    for i in range(3):
        test_file = tmp_path / f"test_file_{i}.json"
        test_file.write_text(f'{{"id": "test_{i}", "value": {i}}}')
        files.append(test_file)
    
    # Create batch
    print(f"\n1. Creating batch for dataset {test_dataset_id}...")
    batch = await catalog_client.create_batch(
        dataset_id=test_dataset_id,
        format="json"
    )
    print(f"   ✓ Batch created: {batch.id}")
    
    # Upload multiple files
    print(f"2. Uploading {len(files)} files concurrently...")
    results = await bulk_client.upload_multiple_files(
        file_paths=files,
        batch_id=batch.id,
        max_concurrent=3
    )
    
    # Verify all uploads succeeded
    assert len(results) == 3
    for result in results:
        assert result["success"] is True
        print(f"   ✓ {result['file_name']}: {result['size_bytes']} bytes")
    
    # Complete batch
    print("3. Completing batch...")
    await catalog_client.complete_batch(batch.id)
    print(f"   ✓ Batch marked as complete")
    
    # Wait for processing
    print("4. Waiting for batch processing...")
    try:
        final_batch = await catalog_client.wait_for_batch_completion(
            batch_id=batch.id,
            timeout=300,
            poll_interval=5
        )
        print(f"   ✓ Status: {final_batch.status.value}")
        assert final_batch.status in [BatchStatus.SUCCESS, BatchStatus.ACTIVE]
    except asyncio.TimeoutError:
        pytest.fail("Batch processing timed out")


@pytest.mark.asyncio
async def test_end_to_end_directory_upload(
    catalog_client: CatalogServiceClient,
    bulk_client: BulkIngestClient,
    test_dataset_id: str,
    tmp_path: Path,
):
    """Test uploading all files from a directory with pattern matching."""
    # Create test directory with multiple files
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    # Create JSON files
    for i in range(3):
        (data_dir / f"data_{i}.json").write_text(f'{{"id": {i}}}')
    
    # Create CSV file (should be ignored with *.json pattern)
    (data_dir / "data.csv").write_text("id,value\n1,test")
    
    # Create batch
    print(f"\n1. Creating batch for dataset {test_dataset_id}...")
    batch = await catalog_client.create_batch(
        dataset_id=test_dataset_id,
        format="json"
    )
    print(f"   ✓ Batch created: {batch.id}")
    
    # Upload directory with *.json pattern
    print(f"2. Uploading directory {data_dir} with pattern '*.json'...")
    results = await bulk_client.upload_directory(
        directory=data_dir,
        batch_id=batch.id,
        pattern="*.json",
        recursive=False,
        max_concurrent=3
    )
    
    # Verify only JSON files uploaded (CSV should be excluded)
    assert len(results) == 3
    for result in results:
        assert result["success"] is True
        assert result["file_name"].endswith(".json")
        print(f"   ✓ {result['file_name']}")
    
    # Complete batch
    print("3. Completing batch...")
    await catalog_client.complete_batch(batch.id)
    print(f"   ✓ Batch marked as complete")


@pytest.mark.asyncio
async def test_batch_abort_workflow(
    catalog_client: CatalogServiceClient,
    bulk_client: BulkIngestClient,
    test_dataset_id: str,
    temp_test_file: Path,
):
    """Test aborting a batch after uploading files."""
    # Create batch
    print(f"\n1. Creating batch for dataset {test_dataset_id}...")
    batch = await catalog_client.create_batch(
        dataset_id=test_dataset_id,
        format="json"
    )
    print(f"   ✓ Batch created: {batch.id}")
    
    # Upload file
    print("2. Uploading file...")
    result = await bulk_client.upload_file(
        file_path=temp_test_file,
        batch_id=batch.id
    )
    assert result["success"] is True
    print(f"   ✓ File uploaded")
    
    # Abort batch instead of completing
    print("3. Aborting batch...")
    await catalog_client.abort_batch(batch.id)
    print(f"   ✓ Batch aborted")
    
    # Verify batch status
    print("4. Verifying batch status...")
    final_batch = await catalog_client.get_batch(batch.id)
    assert final_batch.status == BatchStatus.ABORTED
    print(f"   ✓ Batch status confirmed: {final_batch.status.value}")


@pytest.mark.asyncio
async def test_large_file_upload(
    catalog_client: CatalogServiceClient,
    bulk_client: BulkIngestClient,
    test_dataset_id: str,
    tmp_path: Path,
):
    """Test uploading a larger file (>1MB) to verify no size issues.
    
    Note: This doesn't test chunked uploads (>10MB) as that would be too slow
    for regular testing. Chunked uploads should be tested manually.
    """
    # Create 2MB test file
    large_file = tmp_path / "large_test.json"
    large_data = '{"id": "test", "data": "' + ('x' * 2_000_000) + '"}'
    large_file.write_text(large_data)
    
    print(f"\n1. Creating batch for dataset {test_dataset_id}...")
    batch = await catalog_client.create_batch(
        dataset_id=test_dataset_id,
        format="json"
    )
    print(f"   ✓ Batch created: {batch.id}")
    
    # Upload large file
    print(f"2. Uploading large file ({large_file.stat().st_size:,} bytes)...")
    result = await bulk_client.upload_file(
        file_path=large_file,
        batch_id=batch.id
    )
    assert result["success"] is True
    print(f"   ✓ Large file uploaded: {result['size_bytes']:,} bytes")
    
    # Complete batch
    print("3. Completing batch...")
    await catalog_client.complete_batch(batch.id)
    print(f"   ✓ Batch marked as complete")


# Manual test instructions
"""
To run integration tests:

1. Set environment variables:
   $env:TEST_DATASET_ID="your_dataset_id_here"

2. Ensure Adobe AEP credentials are configured:
   - Either in ~/.adobe/credentials.json
   - Or via environment variables (CLIENT_ID, CLIENT_SECRET, ORG_ID, SANDBOX_NAME)

3. Run tests:
   pytest tests/test_ingestion_integration.py -v --integration

4. Run specific test:
   pytest tests/test_ingestion_integration.py::test_end_to_end_single_file_upload -v --integration

Note: These tests will create real batches in your AEP sandbox. They will be marked
as complete or aborted, so they won't affect production data, but will consume API quota.
"""
