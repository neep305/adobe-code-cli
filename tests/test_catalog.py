"""Unit tests for Catalog Service client."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from adobe_experience.catalog.client import CatalogServiceClient
from adobe_experience.catalog.models import (
    Batch,
    BatchStatus,
    Dataset,
    DatasetSchemaRef,
    DatasetTags,
    DataSetFile,
)


@pytest.fixture
def mock_aep_client():
    """Mock AEPClient for testing."""
    client = AsyncMock()
    client.config = MagicMock()
    return client


@pytest.fixture
def sample_dataset_response():
    """Sample dataset API response."""
    return {
        "@id": "5c8c3c555033b814b69f947f",
        "name": "Test Customer Events",
        "schemaRef": {
            "id": "https://ns.adobe.com/tenant/schemas/test",
            "contentType": "application/vnd.adobe.xed+json;version=1"
        },
        "description": "Test dataset",
        "state": "ENABLED",
        "created": 1234567890000,
        "updated": 1234567890000,
        "imsOrg": "test_org@AdobeOrg"
    }


@pytest.fixture
def sample_batch_response():
    """Sample batch API response."""
    return {
        "id": "5d01230fc78a4e4f8c0c6b387b4b8d1c",
        "imsOrg": "test_org@AdobeOrg",
        "status": "loading",
        "created": 1552694873602,
        "updated": 1552694873602,
        "relatedObjects": [{"type": "dataSet", "id": "test_dataset"}],
        "version": "1.0.0",
        "inputFormat": {"format": "parquet"}
    }


# ==================== Dataset Tests ====================


@pytest.mark.asyncio
async def test_create_dataset(mock_aep_client):
    """Test dataset creation."""
    mock_aep_client.post.return_value = ["@/dataSets/5c8c3c555033b814b69f947f"]

    catalog = CatalogServiceClient(mock_aep_client)
    dataset_id = await catalog.create_dataset(
        name="Test Dataset",
        schema_id="https://ns.adobe.com/tenant/schemas/test"
    )

    assert dataset_id == "5c8c3c555033b814b69f947f"
    mock_aep_client.post.assert_called_once()
    call_args = mock_aep_client.post.call_args
    assert call_args[0][0] == "/data/foundation/catalog/dataSets"
    assert call_args[1]["json"]["name"] == "Test Dataset"


@pytest.mark.asyncio
async def test_create_dataset_with_profile_enabled(mock_aep_client):
    """Test dataset creation with Profile enabled."""
    mock_aep_client.post.return_value = ["@/dataSets/5c8c3c555033b814b69f947f"]

    catalog = CatalogServiceClient(mock_aep_client)
    dataset_id = await catalog.create_dataset(
        name="Profile Dataset",
        schema_id="https://ns.adobe.com/xdm/context/profile",
        enable_profile=True,
        enable_identity=True
    )

    assert dataset_id == "5c8c3c555033b814b69f947f"
    call_args = mock_aep_client.post.call_args
    assert "tags" in call_args[1]["json"]
    assert "unifiedProfile" in call_args[1]["json"]["tags"]
    assert "unifiedIdentity" in call_args[1]["json"]["tags"]


@pytest.mark.asyncio
async def test_create_dataset_already_exists(mock_aep_client):
    """Test dataset creation when name already exists."""
    mock_aep_client.post.side_effect = Exception("409: Dataset already exists")

    catalog = CatalogServiceClient(mock_aep_client)
    with pytest.raises(ValueError, match="already exists"):
        await catalog.create_dataset(
            name="Duplicate Dataset",
            schema_id="https://ns.adobe.com/tenant/schemas/test"
        )


@pytest.mark.asyncio
async def test_list_datasets(mock_aep_client, sample_dataset_response):
    """Test listing datasets."""
    mock_aep_client.get.return_value = {
        "5c8c3c555033b814b69f947f": {
            "name": "Customer Events",
            "schemaRef": {
                "id": "https://ns.adobe.com/tenant/schemas/test",
                "contentType": "application/vnd.adobe.xed+json;version=1"
            },
            "state": "ENABLED",
            "created": 1234567890000,
            "updated": 1234567890000,
            "imsOrg": "test_org@AdobeOrg"
        }
    }

    catalog = CatalogServiceClient(mock_aep_client)
    datasets = await catalog.list_datasets(limit=10)

    assert len(datasets) == 1
    assert datasets[0].name == "Customer Events"
    assert datasets[0].id == "5c8c3c555033b814b69f947f"
    mock_aep_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_list_datasets_with_filters(mock_aep_client):
    """Test listing datasets with filters."""
    mock_aep_client.get.return_value = {}

    catalog = CatalogServiceClient(mock_aep_client)
    datasets = await catalog.list_datasets(
        limit=20,
        properties=["name", "schemaRef"],
        schema_id="https://ns.adobe.com/tenant/schemas/test"
    )

    assert len(datasets) == 0
    call_args = mock_aep_client.get.call_args
    params = call_args[1]["params"]
    assert params["limit"] == 20
    assert params["properties"] == "name,schemaRef"
    assert params["schemaRef.id"] == "https://ns.adobe.com/tenant/schemas/test"


@pytest.mark.asyncio
async def test_get_dataset(mock_aep_client, sample_dataset_response):
    """Test getting dataset by ID."""
    mock_aep_client.get.return_value = {
        "name": "Customer Events",
        "schemaRef": {
            "id": "https://ns.adobe.com/tenant/schemas/test",
            "contentType": "application/vnd.adobe.xed+json;version=1"
        },
        "state": "ENABLED",
        "created": 1234567890000,
        "updated": 1234567890000,
        "imsOrg": "test_org@AdobeOrg"
    }

    catalog = CatalogServiceClient(mock_aep_client)
    dataset = await catalog.get_dataset("5c8c3c555033b814b69f947f")

    assert dataset.name == "Customer Events"
    assert dataset.id == "5c8c3c555033b814b69f947f"
    mock_aep_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_dataset_not_found(mock_aep_client):
    """Test getting non-existent dataset."""
    mock_aep_client.get.side_effect = Exception("404: Dataset not found")

    catalog = CatalogServiceClient(mock_aep_client)
    with pytest.raises(ValueError, match="Dataset not found"):
        await catalog.get_dataset("nonexistent")


@pytest.mark.asyncio
async def test_update_dataset(mock_aep_client):
    """Test updating dataset properties."""
    mock_aep_client.patch.return_value = {
        "name": "Updated Dataset",
        "description": "New description",
        "schemaRef": {
            "id": "https://ns.adobe.com/tenant/schemas/test",
            "contentType": "application/vnd.adobe.xed+json;version=1"
        },
        "created": 1234567890000,
        "updated": 1234567890001,
        "imsOrg": "test_org@AdobeOrg"
    }

    catalog = CatalogServiceClient(mock_aep_client)
    dataset = await catalog.update_dataset(
        dataset_id="5c8c3c555033b814b69f947f",
        description="New description"
    )

    assert dataset.description == "New description"
    mock_aep_client.patch.assert_called_once()


@pytest.mark.asyncio
async def test_delete_dataset(mock_aep_client):
    """Test deleting dataset."""
    mock_aep_client.delete.return_value = {}

    catalog = CatalogServiceClient(mock_aep_client)
    await catalog.delete_dataset("5c8c3c555033b814b69f947f")

    mock_aep_client.delete.assert_called_once()


@pytest.mark.asyncio
async def test_enable_dataset_for_profile(mock_aep_client):
    """Test enabling dataset for Profile."""
    mock_aep_client.patch.return_value = {
        "name": "Profile Dataset",
        "schemaRef": {
            "id": "https://ns.adobe.com/xdm/context/profile",
            "contentType": "application/vnd.adobe.xed+json;version=1"
        },
        "tags": {
            "unifiedProfile": ["enabled:true"]
        },
        "created": 1234567890000,
        "updated": 1234567890001,
        "imsOrg": "test_org@AdobeOrg"
    }

    catalog = CatalogServiceClient(mock_aep_client)
    dataset = await catalog.enable_dataset_for_profile("5c8c3c555033b814b69f947f")

    assert dataset.tags is not None
    assert dataset.tags.unified_profile == ["enabled:true"]


# ==================== Batch Tests ====================


@pytest.mark.asyncio
async def test_create_batch(mock_aep_client):
    """Test batch creation."""
    mock_aep_client.post.return_value = {
        "id": "5d01230fc78a4e4f8c0c6b387b4b8d1c"
    }

    catalog = CatalogServiceClient(mock_aep_client)
    batch_id = await catalog.create_batch(
        dataset_id="5c8c3c555033b814b69f947f",
        format="json"
    )

    assert batch_id == "5d01230fc78a4e4f8c0c6b387b4b8d1c"
    mock_aep_client.post.assert_called_once()
    call_args = mock_aep_client.post.call_args
    assert call_args[0][0] == "/data/foundation/import/batches"


@pytest.mark.asyncio
async def test_get_batch(mock_aep_client, sample_batch_response):
    """Test getting batch status."""
    mock_aep_client.get.return_value = {
        "5d01230fc78a4e4f8c0c6b387b4b8d1c": sample_batch_response
    }

    catalog = CatalogServiceClient(mock_aep_client)
    batch = await catalog.get_batch("5d01230fc78a4e4f8c0c6b387b4b8d1c")

    assert batch.id == "5d01230fc78a4e4f8c0c6b387b4b8d1c"
    assert batch.status == BatchStatus.LOADING
    mock_aep_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_list_batches(mock_aep_client, sample_batch_response):
    """Test listing batches."""
    mock_aep_client.get.return_value = {
        "5d01230fc78a4e4f8c0c6b387b4b8d1c": sample_batch_response
    }

    catalog = CatalogServiceClient(mock_aep_client)
    batches = await catalog.list_batches(
        limit=10,
        dataset_id="5c8c3c555033b814b69f947f"
    )

    assert len(batches) == 1
    assert batches[0].id == "5d01230fc78a4e4f8c0c6b387b4b8d1c"


@pytest.mark.asyncio
async def test_complete_batch(mock_aep_client):
    """Test completing batch."""
    mock_aep_client.post.return_value = {}

    catalog = CatalogServiceClient(mock_aep_client)
    await catalog.complete_batch("5d01230fc78a4e4f8c0c6b387b4b8d1c")

    mock_aep_client.post.assert_called_once()
    call_args = mock_aep_client.post.call_args
    assert call_args[1]["params"]["action"] == "COMPLETE"


@pytest.mark.asyncio
async def test_abort_batch(mock_aep_client):
    """Test aborting batch."""
    mock_aep_client.post.return_value = {}

    catalog = CatalogServiceClient(mock_aep_client)
    await catalog.abort_batch("5d01230fc78a4e4f8c0c6b387b4b8d1c")

    mock_aep_client.post.assert_called_once()
    call_args = mock_aep_client.post.call_args
    assert call_args[1]["params"]["action"] == "ABORT"


@pytest.mark.asyncio
async def test_wait_for_batch_completion_success(mock_aep_client):
    """Test batch status polling until success."""
    # Simulate: loading -> processing -> success
    mock_responses = [
        {
            "batch1": {
                "id": "batch1",
                "status": "loading",
                "created": 1234,
                "updated": 1234,
                "imsOrg": "org",
                "relatedObjects": []
            }
        },
        {
            "batch1": {
                "id": "batch1",
                "status": "processing",
                "created": 1234,
                "updated": 1235,
                "imsOrg": "org",
                "relatedObjects": []
            }
        },
        {
            "batch1": {
                "id": "batch1",
                "status": "success",
                "created": 1234,
                "updated": 1236,
                "imsOrg": "org",
                "relatedObjects": [],
                "metrics": {
                    "recordsWritten": 1000
                }
            }
        },
    ]
    mock_aep_client.get.side_effect = mock_responses

    catalog = CatalogServiceClient(mock_aep_client)
    batch = await catalog.wait_for_batch_completion("batch1", poll_interval=0.1)

    assert batch.status == BatchStatus.SUCCESS
    assert batch.metrics.records_written == 1000
    assert mock_aep_client.get.call_count == 3


@pytest.mark.asyncio
async def test_wait_for_batch_completion_failure(mock_aep_client):
    """Test batch polling when batch fails."""
    mock_aep_client.get.return_value = {
        "batch1": {
            "id": "batch1",
            "status": "failed",
            "created": 1234,
            "updated": 1235,
            "imsOrg": "org",
            "relatedObjects": [],
            "errors": [
                {"code": "INVALID_DATA", "description": "Invalid JSON format"}
            ],
            "metrics": {
                "failureReason": "Data validation failed"
            }
        }
    }

    catalog = CatalogServiceClient(mock_aep_client)
    with pytest.raises(ValueError, match="Batch batch1 failed"):
        await catalog.wait_for_batch_completion("batch1", poll_interval=0.1)


@pytest.mark.asyncio
async def test_wait_for_batch_completion_timeout(mock_aep_client):
    """Test batch polling timeout."""
    mock_aep_client.get.return_value = {
        "batch1": {
            "id": "batch1",
            "status": "processing",
            "created": 1234,
            "updated": 1235,
            "imsOrg": "org",
            "relatedObjects": []
        }
    }

    catalog = CatalogServiceClient(mock_aep_client)
    with pytest.raises(TimeoutError, match="did not complete within"):
        await catalog.wait_for_batch_completion(
            "batch1",
            timeout=1,
            poll_interval=0.5
        )


# ==================== DataSetFile Tests ====================


@pytest.mark.asyncio
async def test_list_dataset_files(mock_aep_client):
    """Test listing dataset files."""
    mock_aep_client.get.return_value = {
        "file1": {
            "@id": "file1",
            "dataSetId": "dataset1",
            "batchId": "batch1",
            "name": "data.parquet",
            "sizeInBytes": 1024,
            "records": 100,
            "created": 1234567890000
        }
    }

    catalog = CatalogServiceClient(mock_aep_client)
    files = await catalog.list_dataset_files(batch_id="batch1")

    assert len(files) == 1
    assert files[0].file_name == "data.parquet"
    assert files[0].size_bytes == 1024
    assert files[0].records == 100
