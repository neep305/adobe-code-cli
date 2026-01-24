"""AEP API client with authentication and retry logic."""

import asyncio
from typing import Any, Dict, Optional

import httpx

from adobe_experience.core.config import AEPConfig, get_config


class AEPClient:
    """Adobe Experience Platform API client.

    Handles OAuth Server-to-Server authentication, token management,
    and retry logic for AEP API calls.
    """

    def __init__(self, config: Optional[AEPConfig] = None) -> None:
        """Initialize AEP client.

        Args:
            config: AEP configuration. If None, loads from environment.
        """
        self.config = config or get_config()
        self._client: Optional[httpx.AsyncClient] = None
        self._access_token: Optional[str] = None

    async def __aenter__(self) -> "AEPClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.config.aep_api_base_url,
            timeout=self.config.timeout,
        )
        await self._ensure_token()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _ensure_token(self) -> None:
        """Ensure we have a valid access token."""
        if self._access_token is None:
            self._access_token = await self._get_access_token()

    async def _get_access_token(self) -> str:
        """Get OAuth access token from Adobe IMS.

        Returns:
            Access token string.

        Raises:
            httpx.HTTPStatusError: If token request fails.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.aep_ims_token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.config.aep_client_id,
                    "client_secret": self.config.aep_client_secret.get_secret_value(),
                    "scope": "openid,AdobeID,read_organizations,additional_info.projectedProductContext",
                },
            )
            response.raise_for_status()
            return response.json()["access_token"]

    def _get_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Get common headers for AEP API requests.

        Args:
            additional_headers: Additional headers to include.

        Returns:
            Headers dictionary.
        """
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "x-api-key": self.config.aep_client_id,
            "x-gw-ims-org-id": self.config.aep_org_id,
            "x-sandbox-name": self.config.aep_sandbox_name,
            "Content-Type": "application/json",
        }
        if additional_headers:
            headers.update(additional_headers)
        return headers

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method.
            path: API path.
            **kwargs: Additional request arguments.

        Returns:
            Response JSON.

        Raises:
            httpx.HTTPStatusError: If request fails after retries.
        """
        if self._client is None:
            raise RuntimeError("Client not initialized. Use async context manager.")

        headers = self._get_headers(kwargs.pop("headers", None))
        last_exception: Optional[Exception] = None

        for attempt in range(self.config.max_retries):
            try:
                response = await self._client.request(
                    method,
                    path,
                    headers=headers,
                    **kwargs,
                )
                response.raise_for_status()
                if response.status_code == 204:
                    return {}
                return response.json()
            except httpx.HTTPStatusError as e:
                last_exception = e
                # Retry only on 429 (rate limit) or 5xx errors
                if e.response.status_code == 429 or e.response.status_code >= 500:
                    delay = self.config.retry_delay * (2**attempt)
                    await asyncio.sleep(delay)
                    continue
                # For client errors, try to get detailed error message
                try:
                    error_detail = e.response.json()
                    raise httpx.HTTPStatusError(
                        f"{e.response.status_code}: {error_detail}",
                        request=e.request,
                        response=e.response,
                    ) from e
                except Exception:
                    raise
            except httpx.RequestError as e:
                last_exception = e
                delay = self.config.retry_delay * (2**attempt)
                await asyncio.sleep(delay)
                continue

        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected error in request retry loop")

    async def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make GET request.

        Args:
            path: API path.
            params: Query parameters.
            headers: Additional headers.

        Returns:
            Response JSON.
        """
        return await self._request_with_retry("GET", path, params=params, headers=headers)

    async def post(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make POST request.

        Args:
            path: API path.
            json: JSON body.
            headers: Additional headers.

        Returns:
            Response JSON.
        """
        return await self._request_with_retry("POST", path, json=json, headers=headers)

    async def put(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make PUT request.

        Args:
            path: API path.
            json: JSON body.
            headers: Additional headers.

        Returns:
            Response JSON.
        """
        return await self._request_with_retry("PUT", path, json=json, headers=headers)

    async def delete(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make DELETE request.

        Args:
            path: API path.
            headers: Additional headers.

        Returns:
            Response JSON.
        """
        return await self._request_with_retry("DELETE", path, headers=headers)
