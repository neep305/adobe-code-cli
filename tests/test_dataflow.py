"""Unit tests for Flow Service client."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from adobe_experience.flow.client import FlowServiceClient
from adobe_experience.flow.models import (
    Connection,
    ConnectionSpec,
    Dataflow,
    DataflowMetrics,
    DataflowRun,
    DataflowSchedule,
    DataflowState,
    FlowSpec,
    RunStatus,
    SourceConnection,
    TargetConnection,
)


@pytest.fixture
def mock_aep_client():
    """Mock AEPClient for testing."""
    client = AsyncMock()
    client.config = MagicMock()
    return client


@pytest.fixture
def sample_dataflow_response():
    """Sample dataflow API response."""
    return {
        "id": "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a",
        "name": "Customer Data Ingestion",
        "description": "Daily customer data sync from S3",
        "flowSpec": {
            "id": "9753525b-82c7-4dce-8a9b-5ccfce2b9876",
            "version": "1.0"
        },
        "sourceConnectionIds": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
        "targetConnectionIds": ["b2c3d4e5-f6a7-8901-bcde-f12345678901"],
        "scheduleParams": {
            "startTime": 1617235200,
            "interval": 86400,
            "frequency": "day"
        },
        "state": "enabled",
        "createdAt": 1617235200000,
        "updatedAt": 1617321600000,
        "createdBy": "test_user@AdobeID",
        "etag": "\"1a2b3c4d\""
    }


@pytest.fixture
def sample_run_response():
    """Sample dataflow run API response."""
    return {
        "id": "run-12345678-abcd-ef01-2345-6789abcdef01",
        "flowId": "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a",
        "status": {
            "value": "success",
            "errors": []
        },
        "metrics": {
            "recordsRead": 10000,
            "recordsWritten": 10000,
            "filesRead": 1,
            "recordsFailed": 0,
            "durationSummary": {
                "startedAtUTC": 1617235200000,
                "completedAtUTC": 1617235500000
            }
        },
        "activities": [
            {
                "id": "activity-1",
                "activityType": "ingestion",
                "status": "success",
                "durationSummary": {
                    "startedAtUTC": 1617235200000,
                    "completedAtUTC": 1617235500000
                }
            }
        ],
        "createdAt": 1617235200000,
        "updatedAt": 1617235500000,
        "etag": "\"abc123\""
    }


@pytest.fixture
def sample_failed_run_response():
    """Sample failed dataflow run API response."""
    return {
        "id": "run-failed-1234-abcd-ef01-2345-6789abcdef",
        "flowId": "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a",
        "status": {
            "value": "failed",
            "errors": [
                {
                    "code": "CONNECTOR-400",
                    "message": "Invalid credentials for source connection",
                    "details": {
                        "connector": "s3",
                        "errorType": "AuthenticationError"
                    }
                }
            ]
        },
        "metrics": {
            "recordsRead": 0,
            "recordsWritten": 0,
            "recordsFailed": 0
        },
        "createdAt": 1617235200000,
        "updatedAt": 1617235300000,
        "etag": "\"xyz789\""
    }


@pytest.fixture
def sample_source_connection_response():
    """Sample source connection API response."""
    return {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "name": "S3 Source",
        "baseConnectionId": "base-conn-123",
        "connectionSpec": {
            "id": "ecadc60c-7455-4d65-9f77-8f1b1e6e1a1a",
            "version": "1.0",
            "name": "Amazon S3"
        },
        "params": {
            "s3": {
                "bucketName": "customer-data",
                "folderPath": "/daily-exports"
            }
        },
        "createdAt": 1617235200000,
        "updatedAt": 1617235200000,
        "etag": "\"xyz789\""
    }


@pytest.fixture
def sample_target_connection_response():
    """Sample target connection API response."""
    return {
        "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "name": "Data Lake Target",
        "baseConnectionId": "base-conn-456",
        "connectionSpec": {
            "id": "c604ff05-7f1a-43c0-8e18-33bf874cb11c",
            "version": "1.0",
            "name": "Data Lake"
        },
        "params": {
            "dataSetId": "5e8c8c8e8c8c8c8c8c8c8c8c"
        },
        "createdAt": 1617235200000,
        "updatedAt": 1617235200000,
        "etag": "\"def456\""
    }


# ==================== Dataflow Tests ====================


@pytest.mark.asyncio
async def test_list_dataflows(mock_aep_client, sample_dataflow_response):
    """Test listing dataflows."""
    mock_aep_client.get.return_value = {
        "items": [sample_dataflow_response],
        "_page": {"count": 1}
    }

    flow_client = FlowServiceClient(mock_aep_client)
    dataflows = await flow_client.list_dataflows(limit=50)

    assert len(dataflows) == 1
    assert dataflows[0].id == "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a"
    assert dataflows[0].name == "Customer Data Ingestion"
    assert dataflows[0].state == DataflowState.ENABLED

    mock_aep_client.get.assert_called_once()
    call_args = mock_aep_client.get.call_args
    assert call_args[0][0] == "/data/foundation/flowservice/flows"
    assert call_args[1]["params"]["limit"] == 50


@pytest.mark.asyncio
async def test_list_dataflows_with_filter(mock_aep_client, sample_dataflow_response):
    """Test listing dataflows with property filter."""
    mock_aep_client.get.return_value = {
        "items": [sample_dataflow_response],
        "_page": {"count": 1}
    }

    flow_client = FlowServiceClient(mock_aep_client)
    dataflows = await flow_client.list_dataflows(
        limit=20,
        property_filter="state==enabled"
    )

    assert len(dataflows) == 1
    mock_aep_client.get.assert_called_once()
    call_args = mock_aep_client.get.call_args
    assert call_args[1]["params"]["property"] == "state==enabled"


@pytest.mark.asyncio
async def test_get_dataflow(mock_aep_client, sample_dataflow_response):
    """Test getting a specific dataflow."""
    mock_aep_client.get.return_value = sample_dataflow_response

    flow_client = FlowServiceClient(mock_aep_client)
    dataflow = await flow_client.get_dataflow("d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a")

    assert dataflow.id == "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a"
    assert dataflow.name == "Customer Data Ingestion"
    assert dataflow.state == DataflowState.ENABLED
    assert len(dataflow.source_connection_ids) == 1
    assert len(dataflow.target_connection_ids) == 1

    mock_aep_client.get.assert_called_once_with(
        "/data/foundation/flowservice/flows/d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a"
    )


@pytest.mark.asyncio
async def test_list_dataflows_paginated(mock_aep_client, sample_dataflow_response):
    """Test paginated listing of dataflows."""
    # First page
    first_page = {
        "items": [sample_dataflow_response],
        "_page": {"count": 1, "next": "token123"}
    }
    # Second page
    second_page_flow = sample_dataflow_response.copy()
    second_page_flow["id"] = "flow-id-2"
    second_page = {
        "items": [second_page_flow],
        "_page": {"count": 1}
    }

    mock_aep_client.get.side_effect = [first_page, second_page]

    flow_client = FlowServiceClient(mock_aep_client)
    dataflows = await flow_client.list_dataflows_paginated(limit=1, max_pages=2)

    assert len(dataflows) == 2
    assert dataflows[0].id == "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a"
    assert dataflows[1].id == "flow-id-2"
    assert mock_aep_client.get.call_count == 2


# ==================== Run Tests ====================


@pytest.mark.asyncio
async def test_list_runs(mock_aep_client, sample_run_response):
    """Test listing runs for a dataflow."""
    mock_aep_client.get.return_value = {
        "items": [sample_run_response],
        "_page": {"count": 1}
    }

    flow_client = FlowServiceClient(mock_aep_client)
    runs = await flow_client.list_runs("d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a", limit=50)

    assert len(runs) == 1
    assert runs[0].id == "run-12345678-abcd-ef01-2345-6789abcdef01"
    assert runs[0].flow_id == "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a"
    assert runs[0].status.value == RunStatus.SUCCESS

    mock_aep_client.get.assert_called_once()
    call_args = mock_aep_client.get.call_args
    assert call_args[0][0] == "/data/foundation/flowservice/runs"
    assert "flowId==d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a" in call_args[1]["params"]["property"]


@pytest.mark.asyncio
async def test_get_run(mock_aep_client, sample_run_response):
    """Test getting a specific run."""
    mock_aep_client.get.return_value = sample_run_response

    flow_client = FlowServiceClient(mock_aep_client)
    run = await flow_client.get_run("run-12345678-abcd-ef01-2345-6789abcdef01")

    assert run.id == "run-12345678-abcd-ef01-2345-6789abcdef01"
    assert run.status.value == RunStatus.SUCCESS
    assert run.metrics.records_read == 10000
    assert run.metrics.records_written == 10000

    mock_aep_client.get.assert_called_once_with(
        "/data/foundation/flowservice/runs/run-12345678-abcd-ef01-2345-6789abcdef01"
    )


@pytest.mark.asyncio
async def test_list_failed_runs(mock_aep_client, sample_run_response, sample_failed_run_response):
    """Test listing only failed runs."""
    mock_aep_client.get.return_value = {
        "items": [sample_run_response, sample_failed_run_response],
        "_page": {"count": 2}
    }

    flow_client = FlowServiceClient(mock_aep_client)
    failed_runs = await flow_client.list_failed_runs("d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a")

    assert len(failed_runs) == 1
    assert failed_runs[0].status.value == RunStatus.FAILED
    assert len(failed_runs[0].status.errors) == 1
    assert failed_runs[0].status.errors[0].code == "CONNECTOR-400"


@pytest.mark.asyncio
async def test_list_runs_by_date_range(mock_aep_client, sample_run_response):
    """Test listing runs by date range."""
    mock_aep_client.get.return_value = {
        "items": [sample_run_response],
        "_page": {"count": 1}
    }

    flow_client = FlowServiceClient(mock_aep_client)
    start_date = datetime(2021, 4, 1)
    end_date = datetime(2021, 4, 7)
    
    runs = await flow_client.list_runs_by_date_range(
        "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a",
        start_date=start_date,
        end_date=end_date
    )

    assert len(runs) == 1
    mock_aep_client.get.assert_called_once()
    call_args = mock_aep_client.get.call_args
    params = call_args[1]["params"]
    assert "flowId==" in params["property"]
    assert "createdAt>=" in params["property"]
    assert "createdAt<=" in params["property"]


# ==================== Connection Tests ====================


@pytest.mark.asyncio
async def test_get_source_connection(mock_aep_client, sample_source_connection_response):
    """Test getting a source connection."""
    mock_aep_client.get.return_value = sample_source_connection_response

    flow_client = FlowServiceClient(mock_aep_client)
    source = await flow_client.get_source_connection("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

    assert source.id == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert source.name == "S3 Source"
    assert source.connection_spec.name == "Amazon S3"

    mock_aep_client.get.assert_called_once_with(
        "/data/foundation/flowservice/sourceConnections/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    )


@pytest.mark.asyncio
async def test_get_target_connection(mock_aep_client, sample_target_connection_response):
    """Test getting a target connection."""
    mock_aep_client.get.return_value = sample_target_connection_response

    flow_client = FlowServiceClient(mock_aep_client)
    target = await flow_client.get_target_connection("b2c3d4e5-f6a7-8901-bcde-f12345678901")

    assert target.id == "b2c3d4e5-f6a7-8901-bcde-f12345678901"
    assert target.name == "Data Lake Target"
    assert target.connection_spec.name == "Data Lake"
    assert target.params["dataSetId"] == "5e8c8c8e8c8c8c8c8c8c8c8c"

    mock_aep_client.get.assert_called_once_with(
        "/data/foundation/flowservice/targetConnections/b2c3d4e5-f6a7-8901-bcde-f12345678901"
    )


@pytest.mark.asyncio
async def test_get_dataflow_connections(
    mock_aep_client,
    sample_dataflow_response,
    sample_source_connection_response,
    sample_target_connection_response
):
    """Test getting all connections for a dataflow."""
    # Mock responses in order: dataflow, source connection, target connection
    mock_aep_client.get.side_effect = [
        sample_dataflow_response,  # get_dataflow
        sample_source_connection_response,  # get_source_connection (parallel)
        sample_target_connection_response,  # get_target_connection (parallel)
    ]

    flow_client = FlowServiceClient(mock_aep_client)
    details = await flow_client.get_dataflow_connections("d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a")

    assert details["dataflow"].id == "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a"
    assert len(details["source_connections"]) == 1
    assert len(details["target_connections"]) == 1
    assert details["source_connections"][0].name == "S3 Source"
    assert details["target_connections"][0].name == "Data Lake Target"


# ==================== Analysis Tests ====================


@pytest.mark.asyncio
async def test_analyze_dataflow_health_all_success(mock_aep_client, sample_run_response):
    """Test health analysis with all successful runs."""
    mock_aep_client.get.return_value = {
        "items": [sample_run_response, sample_run_response],
        "_page": {"count": 2}
    }

    flow_client = FlowServiceClient(mock_aep_client)
    health = await flow_client.analyze_dataflow_health("d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a")

    assert health["total_runs"] == 2
    assert health["success_runs"] == 2
    assert health["failed_runs"] == 0
    assert health["success_rate"] == 100.0
    assert health["average_duration_seconds"] > 0
    assert len(health["errors"]) == 0


@pytest.mark.asyncio
async def test_analyze_dataflow_health_with_failures(
    mock_aep_client,
    sample_run_response,
    sample_failed_run_response
):
    """Test health analysis with some failed runs."""
    mock_aep_client.get.return_value = {
        "items": [sample_run_response, sample_failed_run_response, sample_run_response],
        "_page": {"count": 3}
    }

    flow_client = FlowServiceClient(mock_aep_client)
    health = await flow_client.analyze_dataflow_health("d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a")

    assert health["total_runs"] == 3
    assert health["success_runs"] == 2
    assert health["failed_runs"] == 1
    assert health["success_rate"] == pytest.approx(66.67, rel=0.1)
    assert len(health["errors"]) == 1
    assert health["errors"][0]["code"] == "CONNECTOR-400"


@pytest.mark.asyncio
async def test_analyze_dataflow_health_no_runs(mock_aep_client):
    """Test health analysis with no runs."""
    mock_aep_client.get.return_value = {
        "items": [],
        "_page": {"count": 0}
    }

    flow_client = FlowServiceClient(mock_aep_client)
    health = await flow_client.analyze_dataflow_health("d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a")

    assert health["total_runs"] == 0
    assert health["success_rate"] == 0.0
    assert health["average_duration_seconds"] == 0


# ==================== Model Tests ====================


def test_dataflow_model_parsing(sample_dataflow_response):
    """Test Dataflow model parsing from API response."""
    dataflow = Dataflow(**sample_dataflow_response)

    assert dataflow.id == "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a"
    assert dataflow.name == "Customer Data Ingestion"
    assert dataflow.state == DataflowState.ENABLED
    assert dataflow.flow_spec.id == "9753525b-82c7-4dce-8a9b-5ccfce2b9876"
    assert dataflow.schedule_params.frequency == "day"


def test_run_model_parsing(sample_run_response):
    """Test DataflowRun model parsing from API response."""
    run = DataflowRun(**sample_run_response)

    assert run.id == "run-12345678-abcd-ef01-2345-6789abcdef01"
    assert run.flow_id == "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a"
    assert run.status.value == RunStatus.SUCCESS
    assert len(run.status.errors) == 0
    assert run.metrics.records_read == 10000


def test_failed_run_model_parsing(sample_failed_run_response):
    """Test DataflowRun model parsing with errors."""
    run = DataflowRun(**sample_failed_run_response)

    assert run.status.value == RunStatus.FAILED
    assert len(run.status.errors) == 1
    assert run.status.errors[0].code == "CONNECTOR-400"
    assert run.status.errors[0].message == "Invalid credentials for source connection"


def test_source_connection_model_parsing(sample_source_connection_response):
    """Test SourceConnection model parsing."""
    source = SourceConnection(**sample_source_connection_response)

    assert source.id == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert source.name == "S3 Source"
    assert source.connection_spec.name == "Amazon S3"
    assert source.params["s3"]["bucketName"] == "customer-data"


def test_target_connection_model_parsing(sample_target_connection_response):
    """Test TargetConnection model parsing."""
    target = TargetConnection(**sample_target_connection_response)

    assert target.id == "b2c3d4e5-f6a7-8901-bcde-f12345678901"
    assert target.name == "Data Lake Target"
    assert target.connection_spec.name == "Data Lake"
    assert target.params["dataSetId"] == "5e8c8c8e8c8c8c8c8c8c8c8c"
