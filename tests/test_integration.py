"""Integration tests for AEP API client."""

import os

import pytest

from adobe_experience.aep.client import AEPClient
from adobe_experience.core.config import AEPConfig

# Skip integration tests if credentials are not configured
pytestmark = pytest.mark.skipif(
    not os.getenv("AEP_CLIENT_ID"),
    reason="AEP credentials not configured - set AEP_CLIENT_ID to run integration tests",
)


@pytest.mark.asyncio
async def test_authentication():
    """Test OAuth authentication flow."""
    async with AEPClient() as client:
        token = await client._get_access_token()
        assert token is not None
        assert len(token) > 0
        assert client._token is not None
        assert client._token.token_type == "bearer"
        assert client._token.expires_in > 0


@pytest.mark.asyncio
async def test_token_caching():
    """Test that tokens are cached and reused."""
    async with AEPClient() as client:
        token1 = await client._get_access_token()
        token2 = await client._get_access_token()
        
        # Should return same token
        assert token1 == token2
        assert client._token.created_at > 0


@pytest.mark.asyncio
async def test_list_schemas():
    """Test listing schemas from Schema Registry."""
    async with AEPClient() as client:
        result = await client.get(
            "/data/foundation/schemaregistry/tenant/schemas",
            params={"limit": 10},
            headers={"Accept": "application/vnd.adobe.xed-id+json"},
        )
        
        assert "results" in result or "_page" in result


@pytest.mark.asyncio
async def test_sandbox_isolation():
    """Test that sandbox name is properly sent in headers."""
    config = AEPConfig()
    
    async with AEPClient(config) as client:
        token = await client._get_access_token()
        headers = client._get_headers(token)
        
        assert "x-sandbox-name" in headers
        assert headers["x-sandbox-name"] == config.aep_sandbox_name


@pytest.mark.asyncio
async def test_error_handling_401():
    """Test handling of authentication errors."""
    # Create client with invalid credentials
    config = AEPConfig(
        aep_client_id="invalid_id",
        aep_client_secret="invalid_secret",
        aep_org_id="invalid_org@AdobeOrg",
        aep_technical_account_id="invalid@techacct.adobe.com",
    )
    
    async with AEPClient(config) as client:
        with pytest.raises(Exception):  # Should raise authentication error
            await client._get_access_token()


@pytest.mark.asyncio
async def test_retry_on_rate_limit():
    """Test retry logic on rate limiting (429).
    
    Note: This is hard to test without actually triggering rate limits.
    This is a smoke test to ensure the retry mechanism doesn't break.
    """
    async with AEPClient() as client:
        # Normal request should work
        result = await client.get(
            "/data/foundation/schemaregistry/tenant/schemas",
            params={"limit": 1},
            headers={"Accept": "application/vnd.adobe.xed-id+json"},
        )
        
        assert result is not None


# ==================== Flow Service Integration Tests ====================


@pytest.mark.asyncio
async def test_list_dataflows():
    """Test listing dataflows from Flow Service."""
    from adobe_experience.flow.client import FlowServiceClient
    
    async with AEPClient() as aep_client:
        flow_client = FlowServiceClient(aep_client)
        dataflows = await flow_client.list_dataflows(limit=10)
        
        # Should return a list (could be empty in test sandbox)
        assert isinstance(dataflows, list)
        
        # If dataflows exist, verify structure
        if dataflows:
            flow = dataflows[0]
            assert flow.id is not None
            assert flow.name is not None
            assert flow.state is not None
            assert flow.flow_spec is not None


@pytest.mark.asyncio
async def test_get_dataflow_details():
    """Test getting dataflow details.
    
    Note: This test requires at least one dataflow to exist in the sandbox.
    """
    from adobe_experience.flow.client import FlowServiceClient
    
    async with AEPClient() as aep_client:
        flow_client = FlowServiceClient(aep_client)
        dataflows = await flow_client.list_dataflows(limit=1)
        
        if dataflows:
            # Test getting details for the first dataflow
            flow_id = dataflows[0].id
            flow_detail = await flow_client.get_dataflow(flow_id)
            
            assert flow_detail.id == flow_id
            assert flow_detail.name is not None
            assert flow_detail.source_connection_ids is not None
            assert flow_detail.target_connection_ids is not None
            assert flow_detail.created_at > 0
        else:
            pytest.skip("No dataflows available in test sandbox")


@pytest.mark.asyncio
async def test_list_dataflow_runs():
    """Test listing runs for a dataflow.
    
    Note: This test requires at least one dataflow with runs.
    """
    from adobe_experience.flow.client import FlowServiceClient
    
    async with AEPClient() as aep_client:
        flow_client = FlowServiceClient(aep_client)
        dataflows = await flow_client.list_dataflows(limit=5)
        
        if dataflows:
            # Try to find a dataflow with runs
            for flow in dataflows:
                runs = await flow_client.list_runs(flow.id, limit=5)
                if runs:
                    # Verify run structure
                    run = runs[0]
                    assert run.id is not None
                    assert run.flow_id == flow.id
                    assert run.status is not None
                    assert run.created_at > 0
                    return  # Test passed
            
            pytest.skip("No dataflow runs available in test sandbox")
        else:
            pytest.skip("No dataflows available in test sandbox")


@pytest.mark.asyncio
async def test_get_dataflow_connections():
    """Test getting connection details for a dataflow.
    
    Note: This test requires at least one dataflow with connections.
    """
    from adobe_experience.flow.client import FlowServiceClient
    
    async with AEPClient() as aep_client:
        flow_client = FlowServiceClient(aep_client)
        dataflows = await flow_client.list_dataflows(limit=1)
        
        if dataflows:
            flow_id = dataflows[0].id
            details = await flow_client.get_dataflow_connections(flow_id)
            
            assert "dataflow" in details
            assert "source_connections" in details
            assert "target_connections" in details
            assert details["dataflow"].id == flow_id
            
            # Verify connections are retrieved (if they exist)
            assert isinstance(details["source_connections"], list)
            assert isinstance(details["target_connections"], list)
        else:
            pytest.skip("No dataflows available in test sandbox")


@pytest.mark.asyncio
async def test_analyze_dataflow_health():
    """Test dataflow health analysis.
    
    Note: This test requires at least one dataflow with run history.
    """
    from adobe_experience.flow.client import FlowServiceClient
    
    async with AEPClient() as aep_client:
        flow_client = FlowServiceClient(aep_client)
        dataflows = await flow_client.list_dataflows(limit=5)
        
        if dataflows:
            # Analyze health for the first dataflow
            flow_id = dataflows[0].id
            health = await flow_client.analyze_dataflow_health(flow_id, lookback_days=7)
            
            # Verify health report structure
            assert "total_runs" in health
            assert "success_rate" in health
            assert "failed_runs" in health
            assert "success_runs" in health
            assert "errors" in health
            
            assert health["total_runs"] >= 0
            assert 0 <= health["success_rate"] <= 100
        else:
            pytest.skip("No dataflows available in test sandbox")

