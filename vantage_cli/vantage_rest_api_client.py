"""Vantage REST API Client for License Management and related resources."""

import inspect
import json as json_lib
import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional

import httpx
import typer
from rich.console import Console
from rich.json import JSON

from .auth import refresh_access_token_standalone
from .cache import save_tokens_to_cache
from .config import Settings

logger = logging.getLogger(__name__)


class VantageRestApiClient:
    """REST API client for Vantage platform services.

    Provides authenticated HTTP request capabilities for interacting with
    Vantage APIs. Handles authentication, request construction, and error handling.
    """

    def __init__(
        self,
        ctx: typer.Context,
        timeout: int = 30,
        base_path: str = "",
    ):
        apis_url = ctx.obj.settings.get_apis_url().rstrip("/")
        self.base_url = f"{apis_url}{base_path}" if base_path else apis_url
        self.persona = ctx.obj.persona
        self.profile = ctx.obj.profile
        self.settings = ctx.obj.settings or Settings()
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
        """Make an authenticated HTTP request to the Vantage API.

        Handles automatic token refresh on 401/403 errors and provides
        consistent error handling and response parsing.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            path: API endpoint path relative to base_url
            **kwargs: Additional arguments to pass to httpx.request

        Returns:
            Parsed JSON response or text content

        Raises:
            httpx.HTTPStatusError: On HTTP errors after retry exhaustion
            Exception: On other request failures
        """
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
        """Send GET request to the API.

        Args:
            path: API endpoint path
            params: Optional query parameters

        Returns:
            Response data
        """
        return await self.request("GET", path, params=params)

    async def post(self, path: str, json: Optional[Dict[str, Any]] = None) -> Any:
        """Send POST request to the API.

        Args:
            path: API endpoint path
            json: Optional JSON body

        Returns:
            Response data
        """
        return await self.request("POST", path, json=json)

    async def put(self, path: str, json: Optional[Dict[str, Any]] = None) -> Any:
        """Send PUT request to the API.

        Args:
            path: API endpoint path
            json: Optional JSON body

        Returns:
            Response data
        """
        return await self.request("PUT", path, json=json)

    async def delete(self, path: str) -> Any:
        """Send DELETE request to the API.

        Args:
            path: API endpoint path

        Returns:
            Response data
        """
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
        """Close the HTTP client connection."""
        await self.client.aclose()


def attach_vantage_rest_client(
    func: Optional[Callable[..., Any]] = None, base_path: str = ""
) -> Callable[..., Any]:
    """Attach VantageRestApiClient to the CLI context.

    This decorator automatically initializes a VantageRestApiClient using the
    persona and settings from the context, and attaches it to ctx.obj.rest_client.

    Prerequisites:
        - @attach_settings must be applied before this decorator
        - @attach_persona must be applied before this decorator

    Usage:
        @attach_settings
        @attach_persona
        @attach_vantage_rest_client
        async def my_command(ctx: typer.Context):
            # ctx.obj.rest_client is now available
            result = await ctx.obj.rest_client.get("/licenses")

        # For jobbergate endpoints:
        @attach_settings
        @attach_persona
        @attach_vantage_rest_client(base_path="/jobbergate")
        async def job_command(ctx: typer.Context):
            result = await ctx.obj.rest_client.get("/job-scripts")
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(ctx: typer.Context, *args, **kwargs):
                # Ensure we have settings and persona
                if not hasattr(ctx.obj, "settings") or ctx.obj.settings is None:
                    raise RuntimeError(
                        "@attach_vantage_rest_client requires @attach_settings to be applied first"
                    )

                if not hasattr(ctx.obj, "persona") or ctx.obj.persona is None:
                    raise RuntimeError(
                        "@attach_vantage_rest_client requires @attach_persona to be applied first"
                    )

                # Create and attach the REST client with base_path
                ctx.obj.rest_client = VantageRestApiClient(ctx=ctx, base_path=base_path)
                if ctx.obj.verbose:
                    full_url = (
                        f"{ctx.obj.settings.get_apis_url()}{base_path}"
                        if base_path
                        else ctx.obj.settings.get_apis_url()
                    )
                    ctx.obj.console.log(f"Attached REST API client for {full_url}")

                try:
                    return await func(ctx, *args, **kwargs)
                finally:
                    # Clean up the client
                    await ctx.obj.rest_client.close()

            return async_wrapper
        else:

            @wraps(func)
            def wrapper(ctx: typer.Context, *args, **kwargs):
                # Ensure we have settings and persona
                if not hasattr(ctx.obj, "settings") or ctx.obj.settings is None:
                    raise RuntimeError(
                        "@attach_vantage_rest_client requires @attach_settings to be applied first"
                    )

                if not hasattr(ctx.obj, "persona") or ctx.obj.persona is None:
                    raise RuntimeError(
                        "@attach_vantage_rest_client requires @attach_persona to be applied first"
                    )

                # Create and attach the REST client (sync version - user must manage cleanup)
                ctx.obj.rest_client = VantageRestApiClient(ctx=ctx, base_path=base_path)
                if ctx.obj.verbose:
                    full_url = (
                        f"{ctx.obj.settings.get_apis_url()}{base_path}"
                        if base_path
                        else ctx.obj.settings.get_apis_url()
                    )
                    ctx.obj.console.log(f"Attached REST API client for {full_url}")
                # Note: Sync functions must manually close the client if needed
                return func(ctx, *args, **kwargs)

            return wrapper

    # Handle decorator with or without parentheses
    if func is None:
        # Called with parentheses: @attach_vantage_rest_client(base_path="/jobbergate")
        return decorator
    else:
        # Called without parentheses: @attach_vantage_rest_client
        return decorator(func)


def create_vantage_rest_client(ctx: typer.Context, base_path: str = "") -> VantageRestApiClient:
    """Create and return a VantageRestApiClient instance from the Typer context.

    Args:
        ctx: Typer context containing settings and persona
        base_path: Optional base path to prepend to all API calls (e.g., "/jobbergate")

    Returns:
        VantageRestApiClient configured with the specified base path
    """
    if not hasattr(ctx.obj, "settings") or ctx.obj.settings is None:
        raise RuntimeError("Settings must be configured in context before creating REST client")

    if not hasattr(ctx.obj, "persona") or ctx.obj.persona is None:
        raise RuntimeError("Persona must be configured in context before creating REST client")

    return VantageRestApiClient(ctx=ctx, base_path=base_path)
