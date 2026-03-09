"""Unit tests for Segmentation Service client."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from adobe_experience.segmentation.client import SegmentationServiceClient
from adobe_experience.segmentation.models import (
    PQLExpression,
    SegmentDefinition,
    SegmentEstimate,
    SegmentJob,
    SegmentJobStatus,
    SegmentStatus,
)


@pytest.fixture
def mock_aep_client():
    """Mock AEPClient for testing."""
    client = AsyncMock()
    client.config = MagicMock()
    return client


@pytest.fixture
def sample_segment_response():
    """Sample segment definition API response."""
    return {
        "id": "seg-abc123-def456-ghi789",
        "name": "High Value Customers",
        "description": "Customers with total spend > $1000",
        "expression": {
            "type": "PQL",
            "format": "pql/text",
            "value": "person.totalSpent > 1000"
        },
        "schema": {"name": "_xdm.context.profile"},
        "status": "ACTIVE",
        "ttlInDays": 30,
        "created": 1617235200000,
        "updated": 1617321600000,
        "createdBy": "test_user@AdobeID"
    }


@pytest.fixture
def sample_segment_job_response():
    """Sample segment job API response."""
    return {
        "id": "job-12345678-abcd-ef01-2345-6789abcdef",
        "status": "SUCCEEDED",
        "segments": ["seg-abc123-def456-ghi789"],
        "computeJobId": 12345,
        "metrics": {
            "totalTime": 30000,
            "profileSegmentationTime": 25000,
            "segmentedProfileCounter": {"qualifying": 5432}
        },
        "created": 1617235200000,
        "updated": 1617235230000,
        "requestId": "req-xyz789"
    }


@pytest.fixture
def sample_estimate_response():
    """Sample segment estimate API response."""
    return {
        "estimatedSize": 5432,
        "confidenceInterval": "95%"
    }


class TestSegmentationServiceClient:
    """Test cases for SegmentationServiceClient."""

    @pytest.mark.asyncio
    async def test_create_segment(self, mock_aep_client, sample_segment_response):
        """Test creating a segment definition."""
        mock_aep_client.post = AsyncMock(return_value=sample_segment_response)
        
        client = SegmentationServiceClient(mock_aep_client)
        segment_id = await client.create_segment(
            name="High Value Customers",
            pql_expression="person.totalSpent > 1000",
            description="Customers with total spend > $1000"
        )
        
        assert segment_id == "seg-abc123-def456-ghi789"
        mock_aep_client.post.assert_called_once()
        
        # Verify request payload
        call_args = mock_aep_client.post.call_args
        assert call_args[0][0] == "/data/core/ups/segment/definitions"
        payload = call_args[1]["json"]
        assert payload["name"] == "High Value Customers"
        assert payload["expression"]["value"] == "person.totalSpent > 1000"

    @pytest.mark.asyncio
    async def test_list_segments(self, mock_aep_client, sample_segment_response):
        """Test listing segment definitions."""
        mock_aep_client.get = AsyncMock(return_value={
            "children": [sample_segment_response],
            "_page": {"count": 1}
        })
        
        client = SegmentationServiceClient(mock_aep_client)
        segments = await client.list_segments(limit=20)
        
        assert len(segments) == 1
        assert segments[0].name == "High Value Customers"
        assert segments[0].status == SegmentStatus.ACTIVE
        assert segments[0].expression.value == "person.totalSpent > 1000"

    @pytest.mark.asyncio
    async def test_list_segments_with_status_filter(self, mock_aep_client):
        """Test listing segments with status filter."""
        mock_aep_client.get = AsyncMock(return_value={"children": []})
        
        client = SegmentationServiceClient(mock_aep_client)
        await client.list_segments(status=SegmentStatus.ACTIVE)
        
        # Verify filter was applied
        call_args = mock_aep_client.get.call_args
        params = call_args[1]["params"]
        assert params["property"] == "status==ACTIVE"

    @pytest.mark.asyncio
    async def test_get_segment(self, mock_aep_client, sample_segment_response):
        """Test getting segment details."""
        mock_aep_client.get = AsyncMock(return_value=sample_segment_response)
        
        client = SegmentationServiceClient(mock_aep_client)
        segment = await client.get_segment("seg-abc123-def456-ghi789")
        
        assert segment.id == "seg-abc123-def456-ghi789"
        assert segment.name == "High Value Customers"
        assert segment.status == SegmentStatus.ACTIVE
        assert segment.expression.value == "person.totalSpent > 1000"
        assert segment.created_at is not None

    @pytest.mark.asyncio
    async def test_update_segment(self, mock_aep_client, sample_segment_response):
        """Test updating a segment definition."""
        updated_response = sample_segment_response.copy()
        updated_response["name"] = "Premium Customers"
        updated_response["status"] = "INACTIVE"
        
        mock_aep_client.patch = AsyncMock(return_value=updated_response)
        
        client = SegmentationServiceClient(mock_aep_client)
        segment = await client.update_segment(
            segment_id="seg-abc123-def456-ghi789",
            name="Premium Customers",
            status=SegmentStatus.INACTIVE
        )
        
        assert segment.name == "Premium Customers"
        assert segment.status == SegmentStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_delete_segment(self, mock_aep_client):
        """Test deleting a segment definition."""
        mock_aep_client.delete = AsyncMock()
        
        client = SegmentationServiceClient(mock_aep_client)
        await client.delete_segment("seg-abc123-def456-ghi789")
        
        mock_aep_client.delete.assert_called_once()
        call_args = mock_aep_client.delete.call_args
        assert "seg-abc123-def456-ghi789" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_evaluate_segment(self, mock_aep_client):
        """Test triggering segment evaluation."""
        mock_aep_client.post = AsyncMock(return_value={
            "id": "job-12345678-abcd-ef01-2345-6789abcdef"
        })
        
        client = SegmentationServiceClient(mock_aep_client)
        job_id = await client.evaluate_segment("seg-abc123-def456-ghi789")
        
        assert job_id == "job-12345678-abcd-ef01-2345-6789abcdef"
        mock_aep_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_segment_job(self, mock_aep_client, sample_segment_job_response):
        """Test getting segment job status."""
        mock_aep_client.get = AsyncMock(return_value=sample_segment_job_response)
        
        client = SegmentationServiceClient(mock_aep_client)
        job = await client.get_segment_job("job-12345678-abcd-ef01-2345-6789abcdef")
        
        assert job.id == "job-12345678-abcd-ef01-2345-6789abcdef"
        assert job.status == SegmentJobStatus.SUCCEEDED
        assert len(job.segments) == 1
        assert job.metrics is not None
        assert job.metrics.totalTime == 30000

    @pytest.mark.asyncio
    async def test_list_segment_jobs(self, mock_aep_client, sample_segment_job_response):
        """Test listing segment jobs."""
        mock_aep_client.get = AsyncMock(return_value={
            "children": [sample_segment_job_response]
        })
        
        client = SegmentationServiceClient(mock_aep_client)
        jobs = await client.list_segment_jobs(limit=10)
        
        assert len(jobs) == 1
        assert jobs[0].status == SegmentJobStatus.SUCCEEDED

    @pytest.mark.asyncio
    async def test_estimate_segment_size(self, mock_aep_client, sample_estimate_response):
        """Test estimating segment size."""
        mock_aep_client.post = AsyncMock(return_value=sample_estimate_response)
        
        client = SegmentationServiceClient(mock_aep_client)
        estimate = await client.estimate_segment_size(
            pql_expression="person.age > 25"
        )
        
        assert estimate.estimatedSize == 5432
        assert estimate.confidenceInterval == "95%"

    @pytest.mark.asyncio
    async def test_wait_for_job_completion_success(self, mock_aep_client, sample_segment_job_response):
        """Test waiting for job completion - success case."""
        mock_aep_client.get = AsyncMock(return_value=sample_segment_job_response)
        
        client = SegmentationServiceClient(mock_aep_client)
        job = await client.wait_for_job_completion(
            "job-12345678-abcd-ef01-2345-6789abcdef",
            poll_interval=0.1,
            max_wait=5.0
        )
        
        assert job.status == SegmentJobStatus.SUCCEEDED

    @pytest.mark.asyncio
    async def test_wait_for_job_completion_failure(self, mock_aep_client):
        """Test waiting for job completion - failure case."""
        failed_response = {
            "id": "job-failed",
            "status": "FAILED",
            "segments": ["seg-abc123"],
            "errors": [{"code": "ERR_001", "message": "Evaluation failed"}]
        }
        mock_aep_client.get = AsyncMock(return_value=failed_response)
        
        client = SegmentationServiceClient(mock_aep_client)
        
        with pytest.raises(ValueError, match="Segment job failed"):
            await client.wait_for_job_completion("job-failed", poll_interval=0.1)

    @pytest.mark.asyncio
    async def test_export_segment(self, mock_aep_client):
        """Test exporting segment to dataset."""
        mock_aep_client.post = AsyncMock(return_value={
            "id": "export-job-123"
        })
        
        client = SegmentationServiceClient(mock_aep_client)
        job_id = await client.export_segment(
            segment_id="seg-abc123",
            dataset_id="dataset-xyz789"
        )
        
        assert job_id == "export-job-123"
        
        # Verify payload
        call_args = mock_aep_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["segments"][0]["segmentId"] == "seg-abc123"
        assert payload["destination"]["datasetId"] == "dataset-xyz789"


class TestSegmentDefinitionModel:
    """Test cases for SegmentDefinition model."""

    def test_segment_definition_parsing(self, sample_segment_response):
        """Test parsing segment definition from API response."""
        segment = SegmentDefinition(**sample_segment_response)
        
        assert segment.id == "seg-abc123-def456-ghi789"
        assert segment.name == "High Value Customers"
        assert segment.status == SegmentStatus.ACTIVE
        assert segment.expression.value == "person.totalSpent > 1000"
        assert segment.ttlInDays == 30

    def test_segment_created_at_property(self, sample_segment_response):
        """Test created_at datetime property."""
        segment = SegmentDefinition(**sample_segment_response)
        
        assert segment.created_at is not None
        assert segment.created_at.year == 2021  # Unix timestamp 1617235200000

    def test_pql_expression_model(self):
        """Test PQLExpression model."""
        pql = PQLExpression(
            type="PQL",
            format="pql/text",
            value="person.age > 25 AND person.country == 'US'"
        )
        
        assert pql.type == "PQL"
        assert pql.format == "pql/text"
        assert "person.age > 25" in pql.value


class TestSegmentJobModel:
    """Test cases for SegmentJob model."""

    def test_segment_job_parsing(self, sample_segment_job_response):
        """Test parsing segment job from API response."""
        job = SegmentJob(**sample_segment_job_response)
        
        assert job.id == "job-12345678-abcd-ef01-2345-6789abcdef"
        assert job.status == SegmentJobStatus.SUCCEEDED
        assert len(job.segments) == 1
        assert job.metrics is not None

    def test_segment_job_metrics(self, sample_segment_job_response):
        """Test segment job metrics parsing."""
        job = SegmentJob(**sample_segment_job_response)
        
        assert job.metrics.totalTime == 30000
        assert job.metrics.profileSegmentationTime == 25000
        assert job.metrics.segmentedProfileCounter == {"qualifying": 5432}


class TestSegmentEstimateModel:
    """Test cases for SegmentEstimate model."""

    def test_estimate_parsing(self, sample_estimate_response):
        """Test parsing estimate response."""
        estimate = SegmentEstimate(**sample_estimate_response)
        
        assert estimate.estimatedSize == 5432
        assert estimate.confidenceInterval == "95%"
