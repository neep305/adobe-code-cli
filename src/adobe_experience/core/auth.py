"""Shared authentication utilities for Adobe Experience Cloud products."""

from typing import Dict, Optional
import httpx
from pydantic import SecretStr


class AdobeAuthClient:
    """Adobe IMS authentication client."""
    
    def __init__(
        self,
        client_id: str,
        client_secret: SecretStr,
        org_id: str,
        technical_account_id: str,
        scopes: str = "openid,AdobeID",
        token_url: str = "https://ims-na1.adobelogin.com/ims/token/v3",
    ):
        """Initialize Adobe authentication client.
        
        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
            org_id: IMS organization ID
            technical_account_id: Technical account ID
            scopes: Comma-separated list of scopes
            token_url: Adobe IMS token endpoint URL
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.org_id = org_id
        self.technical_account_id = technical_account_id
        self.scopes = scopes
        self.token_url = token_url
        self._access_token: Optional[str] = None
    
    async def get_access_token(self, force_refresh: bool = False) -> str:
        """Get or refresh access token.
        
        Args:
            force_refresh: Force token refresh even if cached
            
        Returns:
            Valid access token
            
        Raises:
            httpx.HTTPError: If authentication fails
        """
        if self._access_token and not force_refresh:
            return self._access_token
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret.get_secret_value(),
                    "grant_type": "client_credentials",
                    "scope": self.scopes,
                },
            )
            response.raise_for_status()
            
            data = response.json()
            self._access_token = data["access_token"]
            return self._access_token
    
    def get_auth_headers(self, access_token: str) -> Dict[str, str]:
        """Get authentication headers for API requests.
        
        Args:
            access_token: Valid access token
            
        Returns:
            Dictionary of authentication headers
        """
        return {
            "Authorization": f"Bearer {access_token}",
            "x-api-key": self.client_id,
            "x-gw-ims-org-id": self.org_id,
        }
