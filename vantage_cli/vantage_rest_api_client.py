"""Vantage REST API Client for License Management and related resources.
"""

import json as json_lib
from typing import Any, Dict, Optional

import httpx
from loguru import logger
from rich.console import Console
from rich.json import JSON

from .auth import extract_persona, refresh_access_token_standalone
from .cache import load_tokens_from_cache, save_tokens_to_cache
from .config import Settings
from .schemas import Persona


class VantageRestApiClient:
    def __init__(
        self,
        base_url: str,
        persona: Optional[Persona] = None,
        profile: str = "default",
        settings: Optional[Settings] = None,
        timeout: int = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.persona = persona
        self.profile = profile
        self.settings = settings or Settings()
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        self.console = Console()

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "VantageRestApiClient/1.0",
        }

        # Add Bearer token if persona is available
        if self.persona and self.persona.token_set.access_token:
            headers["Authorization"] = f"Bearer {self.persona.token_set.access_token}"

        return headers

    async def _refresh_token_if_needed(self) -> bool:
        """Refresh access token if needed and possible."""
        if not self.persona or not self.persona.token_set.refresh_token:
            return False

        try:
            refresh_success = refresh_access_token_standalone(
                self.persona.token_set, self.settings
            )
            if refresh_success:
                # Save updated tokens to cache
                save_tokens_to_cache(self.profile, self.persona.token_set)
                logger.debug("Successfully refreshed access token")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
            return False

    async def request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url}{path}"
        headers = self._headers()
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        max_auth_retries = 1
        retry_count = 0

        while retry_count <= max_auth_retries:
            try:
                response = await self.client.request(method, url, headers=headers, **kwargs)
                response.raise_for_status()

                if response.headers.get("content-type", "").startswith("application/json"):
                    return response.json()
                return response.text

            except httpx.HTTPStatusError as e:
                # Handle authentication errors with token refresh
                if e.response.status_code in (401, 403) and retry_count < max_auth_retries:
                    logger.debug(
                        f"Authentication error {e.response.status_code}, attempting token refresh"
                    )

                    if await self._refresh_token_if_needed():
                        # Update headers with new token and retry
                        headers = self._headers()
                        retry_count += 1
                        continue

                self.console.print(
                    f"[red]HTTP Error {e.response.status_code}:[/red] {e.response.text}"
                )
                raise
            except Exception as e:
                self.console.print(f"[red]Request failed:[/red] {str(e)}")
                raise

        # Should never reach here due to loop structure
        raise Exception("Unexpected end of request retry loop")

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return await self.request("GET", path, params=params)

    async def post(self, path: str, json: Optional[Dict[str, Any]] = None) -> Any:
        return await self.request("POST", path, json=json)

    async def put(self, path: str, json: Optional[Dict[str, Any]] = None) -> Any:
        return await self.request("PUT", path, json=json)

    async def delete(self, path: str) -> Any:
        return await self.request("DELETE", path)

    def print_json(self, data: Any) -> None:
        """Pretty print JSON data using Rich."""
        if isinstance(data, str):
            try:
                data = json_lib.loads(data)
            except json_lib.JSONDecodeError:
                self.console.print(data)
                return

        json_obj = JSON.from_data(data)
        self.console.print(json_obj)

    async def close(self):
        await self.client.aclose()


def create_vantage_rest_client(
    base_url: str = "https://apis.vantagecompute.ai/lm", profile: str = "default"
) -> VantageRestApiClient:
    """Create a VantageRestApiClient with authentication from cache.

    This function follows the same pattern as create_async_graphql_client
    by automatically loading tokens and creating a persona.

    Args:
        base_url: Base URL for the REST API
        profile: Profile name to use for authentication

    Returns:
        Configured VantageRestApiClient instance

    Raises:
        Exception: If client creation fails
    """
    try:
        # Load tokens and create persona
        token_set = load_tokens_from_cache(profile)
        persona = extract_persona(profile, token_set)

        # Create client with authentication (it will create default settings if needed)
        client = VantageRestApiClient(base_url=base_url, persona=persona, profile=profile)

        logger.debug(f"Created REST API client for {base_url}")
        return client

    except Exception as e:
        logger.error(f"Failed to create REST API client: {e}")
        raise
