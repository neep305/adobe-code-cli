"""Integration tests for AEP API client."""

import os

import pytest

from adobe_aep.aep.client import AEPClient
from adobe_aep.config import AEPConfig

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
