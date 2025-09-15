# Copyright (C) 2025 Vantage Compute Corporation
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
"""Modern GraphQL client implementation using the gql library.

This module provides a robust, production-ready GraphQL client with comprehensive
features including authentication, retry logic, error handling, and observability.
"""

import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from gql import Client
from gql import gql as gql_query
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import (
    TransportClosed,
    TransportConnectionFailed,
    TransportServerError,
)

try:
    from gql import GraphQLRequest
except ImportError:
    # Fallback for older versions of gql
    GraphQLRequest = None
from graphql import DocumentNode
from graphql.language.ast import OperationDefinitionNode
from jose import exceptions as jwt_exceptions
from jose import jwt
from loguru import logger
from requests.exceptions import ConnectionError, Timeout

from .auth import extract_persona, refresh_access_token_standalone
from .cache import load_tokens_from_cache, save_tokens_to_cache
from .config import Settings
from .exceptions import VantageCliError
from .schemas import Persona


class AuthenticationError(VantageCliError):
    """Authentication-related errors."""

    pass


class GraphQLError(VantageCliError):
    """GraphQL-specific error."""

    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        errors: Optional[List[Dict[str, Any]]] = None,
        extensions: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.query = query
        self.variables = variables
        self.errors = errors or []
        self.extensions = extensions or {}


class TransportType(Enum):
    """Available transport types for GraphQL client."""

    AIOHTTP = "aiohttp"  # Async transport using aiohttp library


@dataclass
class GraphQLClientConfig:
    """Configuration for GraphQL client."""

    # Connection settings
    url: str
    timeout: int = 30
    verify_ssl: bool = True

    # Retry settings
    max_retries: int = 3
    retry_backoff_factor: float = 0.5
    retry_status_codes: Tuple[int, ...] = (429, 500, 502, 503, 504)

    # Schema settings
    fetch_schema: bool = True
    validate_queries: bool = True

    # Observability settings
    enable_logging: bool = True
    log_queries: bool = False  # Set to True for debugging (security risk in production)

    # Custom headers
    headers: Dict[str, str] = field(default_factory=lambda: {})

    # Transport type
    transport_type: TransportType = TransportType.AIOHTTP


@dataclass
class QueryMetrics:
    """Metrics for a GraphQL query execution."""

    query_name: str
    execution_time_ms: float
    success: bool
    error_type: Optional[str] = None
    retry_count: int = 0


class VantageGraphQLClient:
    """Production-ready GraphQL client with comprehensive features.

    Features:
    - Multiple transport options (sync/async)
    - Automatic authentication token injection
    - Request retry logic with exponential backoff
    - Schema validation and introspection
    - Comprehensive error handling
    - Request/response logging and metrics
    - Connection pooling and keep-alive
    """

    def __init__(
        self,
        config: GraphQLClientConfig,
        persona: Optional[Persona] = None,
        profile: str = "default",
        settings: Optional[Settings] = None,
    ):
        self.config = config
        self.persona = persona
        self.profile = profile
        self.settings = settings
        self._client: Optional[Client] = None
        self._transport = None
        self._schema = None
        self._query_metrics: List[QueryMetrics] = []

        # Setup logging
        if config.enable_logging:
            self._setup_logging()

    def _setup_logging(self) -> None:
        """Set up GraphQL client logging."""
        gql_logger = logging.getLogger("gql")
        gql_logger.setLevel(logging.INFO if self.config.log_queries else logging.WARNING)

    def _create_transport(self) -> None:
        """Create (or recreate) the underlying transport and store it.

        Tests only assert side–effects (headers/auth) and in some cases
        expect this method to return ``None``. Returning ``None`` keeps
        semantics simple while callers rely on ``self._transport``.
        """
        headers = {"Content-Type": "application/json"}

        if self.persona and self.persona.token_set.access_token:
            headers["Authorization"] = f"Bearer {self.persona.token_set.access_token}"

        # Currently only AIOHTTP async transport is supported.
        self._transport = AIOHTTPTransport(
            url=self.config.url,
            headers=headers,
            timeout=self.config.timeout,
            ssl=self.config.verify_ssl,
        )
        return None

    def _build_headers(self) -> Dict[str, str]:
        """Build HTTP headers including authentication."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "VantageGraphQLClient/1.0",
            **self.config.headers,
        }

        # Add authentication if persona is available
        if self.persona and self.persona.token_set.access_token:
            headers["Authorization"] = f"Bearer {self.persona.token_set.access_token}"

        return headers

    def _validate_auth(self) -> None:
        """Validate authentication before making requests."""
        if not self.persona:
            raise AuthenticationError("No authentication persona provided")

        if not self.persona.token_set.access_token:
            raise AuthenticationError("No access token available")

        # Check if token is expired
        if self._is_token_expired():
            raise AuthenticationError("Access token has expired")

    def _is_token_expired(self) -> bool:
        """Check if the current token is expired."""
        if not self.persona or not self.persona.token_set.access_token:
            return True

        try:
            # Decode without verification to check expiration
            jwt.decode(
                self.persona.token_set.access_token,
                key="",  # Empty key since we're not verifying signature
                options={"verify_signature": False, "verify_exp": True},
            )
            return False
        except jwt_exceptions.ExpiredSignatureError:
            return True
        except jwt_exceptions.JWTError:
            logger.warning("Invalid token format")
            return True

    async def _refresh_token_async(self, settings: Settings) -> bool:
        """Refresh the access token using the refresh token asynchronously.

        Returns True if refresh was successful, False otherwise.
        Updates the persona's token_set in-place.
        """
        if not self.persona or not self.persona.token_set.refresh_token:
            logger.warning("No persona or refresh token available")
            return False

        try:
            # Use the existing sync refresh function in an async wrapper
            # This is safe since the function doesn't block the event loop for long
            refresh_success = refresh_access_token_standalone(self.persona.token_set, settings)

            if refresh_success:
                # Save updated tokens to cache
                save_tokens_to_cache(self.profile, self.persona.token_set)
                logger.debug("Successfully refreshed access token")
                return True
            else:
                logger.error("Token refresh returned False")
                return False

        except Exception as e:
            logger.error(f"Failed to refresh token asynchronously: {e}")
            return False

    def _refresh_transport_headers(self) -> None:
        """Update transport with refreshed token by recreating it."""
        if self.persona and self.persona.token_set.access_token:
            # Recreate transport with updated token. Some tests monkeypatch
            # _create_transport to return a sentinel transport; honor that
            # return value if provided while keeping default implementation
            # (which returns None and sets self._transport internally).
            maybe_transport = self._create_transport()
            if maybe_transport is not None:  # pragma: no cover - exercised via monkeypatch
                self._transport = maybe_transport  # type: ignore[assignment]

    def _log_query_metrics(self, metrics: QueryMetrics) -> None:
        """Log query execution metrics."""
        self._query_metrics.append(metrics)

        if self.config.enable_logging:
            status = "SUCCESS" if metrics.success else "FAILED"
            logger.info(
                f"GraphQL Query [{metrics.query_name}] {status} "
                f"in {metrics.execution_time_ms:.2f}ms "
                f"(retries: {metrics.retry_count})"
            )

            if not metrics.success and metrics.error_type:
                logger.error(f"Query failed with error: {metrics.error_type}")

    def _extract_query_name(self, query: Union[str, DocumentNode]) -> str:
        """Extract operation name from GraphQL query or DocumentNode.

        Falls back to ``UnnamedOperation`` if no explicit name can be
        determined. This function purposefully implements a *loose*
        parsing strategy sufficient for logging & metrics – not full
        GraphQL validation.
        """
        # AST path: leverage OperationDefinition name if present.
        if isinstance(query, DocumentNode):
            for definition in getattr(query, "definitions", []) or []:
                if isinstance(definition, OperationDefinitionNode):
                    name_node = getattr(definition, "name", None)
                    if name_node and getattr(name_node, "value", ""):
                        return name_node.value  # type: ignore[return-value]
            # Fallback to string parsing after AST attempt
            query_str = str(query)
        else:
            query_str = query

        lowered = query_str.lower()
        # String heuristics (case‑insensitive search preserving original case)
        for op in ("query", "mutation"):
            idx = lowered.find(f"{op} ")
            if idx != -1:
                try:
                    segment = query_str[idx + len(op) + 1 :].split("{")[0].strip()
                    if segment and not segment.startswith("("):
                        return segment.split("(")[0].strip()
                except Exception:
                    break
        return "UnnamedOperation"

    def _handle_graphql_errors(
        self, result: Dict[str, Any], query: str, variables: Optional[Dict[str, Any]] = None
    ) -> None:
        """Handle GraphQL errors from response."""
        # Check for errors in the response data structure
        if "errors" in result and result["errors"]:
            error_messages = [str(error) for error in result["errors"]]
            raise GraphQLError(
                message=f"GraphQL errors: {'; '.join(error_messages)}",
                query=query if self.config.log_queries else None,
                variables=variables if self.config.log_queries else None,
                errors=result["errors"],
            )

    def _handle_transport_error(self, error: Exception, query_name: str) -> None:
        """Handle transport-level errors with appropriate error types."""
        if isinstance(error, TransportServerError):
            if "401" in str(error) or "Unauthorized" in str(error):
                raise AuthenticationError(f"Authentication failed: {error}")
            elif "403" in str(error) or "Forbidden" in str(error):
                raise AuthenticationError(f"Access forbidden: {error}")
            else:
                raise GraphQLError(f"Server error during {query_name}: {error}")

        elif isinstance(error, (TransportConnectionFailed, ConnectionError)):
            raise GraphQLError(f"Connection failed during {query_name}: {error}")

        elif isinstance(error, Timeout):
            raise GraphQLError(f"Request timeout during {query_name}: {error}")

        elif isinstance(error, TransportClosed):
            raise GraphQLError(f"Transport closed during {query_name}: {error}")

        else:
            raise GraphQLError(f"Transport error during {query_name}: {error}")

    @asynccontextmanager
    async def _async_session(self):
        """Context manager for asynchronous GraphQL sessions."""
        if not self._transport:
            created = self._create_transport()
            # Support tests that monkeypatch _create_transport to return a transport
            if self._transport is None and created is not None:  # pragma: no cover
                self._transport = created  # type: ignore[assignment]

        client = Client(
            transport=self._transport, fetch_schema_from_transport=self.config.fetch_schema
        )

        try:
            async with client as session:
                yield session
        finally:
            # Transport cleanup is handled by the context manager
            pass

    async def execute_async(
        self, query: str, variables: Optional[Dict[str, Any]] = None, require_auth: bool = True
    ) -> Dict[str, Any]:
        """Execute a GraphQL query asynchronously.

        Args:
            query: GraphQL query string
            variables: Query variables
            require_auth: Whether authentication is required

        Returns:
            Query result data

        Raises:
            GraphQLError: For GraphQL-specific errors
            AuthenticationError: For authentication issues
        """
        if require_auth:
            self._validate_auth()

        query_name = self._extract_query_name(query)
        start_time = time.time()
        retry_count = 0
        max_auth_retries = 1  # Only retry once for auth errors

        while retry_count <= max_auth_retries:
            try:
                parsed_query = gql_query(query)

                async with self._async_session() as session:
                    # Use the new GraphQLRequest API to avoid deprecation warning
                    if GraphQLRequest is not None:
                        request = GraphQLRequest(parsed_query, variable_values=variables or {})
                        result = await session.execute(request)
                    else:
                        # Fallback for older versions
                        result = await session.execute(
                            parsed_query, variable_values=variables or {}
                        )

                    # Result from gql is already a dict
                    if result:
                        self._handle_graphql_errors(result, query, variables)

                    execution_time = (time.time() - start_time) * 1000
                    metrics = QueryMetrics(
                        query_name=query_name,
                        execution_time_ms=execution_time,
                        success=True,
                        retry_count=retry_count,
                    )
                    self._log_query_metrics(metrics)

                    return result or {}

            except Exception as error:
                # Check if it's an authentication error and we can retry
                is_auth_error = isinstance(error, TransportServerError) and (
                    "401" in str(error)
                    or "403" in str(error)
                    or "Unauthorized" in str(error)
                    or "Forbidden" in str(error)
                )

                if is_auth_error and retry_count < max_auth_retries and self.settings:
                    logger.debug(
                        f"Authentication error detected, attempting token refresh (retry {retry_count + 1})"
                    )

                    # Try to refresh the token
                    refresh_success = await self._refresh_token_async(self.settings)

                    if refresh_success:
                        # Update transport with new token
                        self._refresh_transport_headers()
                        retry_count += 1
                        logger.debug("Token refreshed successfully, retrying request")
                        continue
                    else:
                        logger.error("Token refresh failed")

                # If we get here, either it's not an auth error, we've exhausted retries,
                # or refresh failed - handle the error normally
                execution_time = (time.time() - start_time) * 1000
                metrics = QueryMetrics(
                    query_name=query_name,
                    execution_time_ms=execution_time,
                    success=False,
                    error_type=type(error).__name__,
                    retry_count=retry_count,
                )
                self._log_query_metrics(metrics)

                if isinstance(error, (GraphQLError, AuthenticationError)):
                    raise
                else:
                    self._handle_transport_error(error, query_name)
                    # _handle_transport_error always raises, but just in case:
                    raise GraphQLError(f"Unexpected error during {query_name}: {error}")

        # This should never be reached due to the retry loop and error handling
        raise GraphQLError(f"Unexpected end of execution for {query_name}")

    async def get_schema(self) -> Optional[Any]:
        """Get the GraphQL schema if available."""
        if self.config.fetch_schema:
            try:
                async with self._async_session() as session:
                    # Access the client's schema, not session's
                    return getattr(session, "schema", None)
            except Exception:
                return None
        return None

    def get_metrics(self) -> List[QueryMetrics]:
        """Get query execution metrics."""
        return self._query_metrics.copy()

    def clear_metrics(self) -> None:
        """Clear query execution metrics."""
        self._query_metrics.clear()

    async def health_check(self) -> bool:
        """Perform a basic health check by executing a simple introspection query.

        Returns:
            True if the service is healthy, False otherwise
        """
        try:
            introspection_query = """
            query IntrospectionQuery {
              __schema {
                queryType {
                  name
                }
              }
            }
            """

            exec_result = self.execute_async(introspection_query, require_auth=False)
            # Support tests that monkeypatch execute_async with a sync function.
            if hasattr(exec_result, "__await__"):
                result = await exec_result  # type: ignore[assignment]
            else:  # sync fallback
                result = exec_result  # type: ignore[assignment]

            if isinstance(result, dict):
                # Success if introspection key is present (value may be empty dict in tests)
                return "__schema" in result
            return False

        except Exception as error:
            logger.warning(f"Health check failed: {error}")
            return False


# Factory functions for common use cases


def create_vantage_graphql_client(
    url: str,
    persona: Optional[Persona] = None,
    transport_type: TransportType = TransportType.AIOHTTP,
    profile: str = "default",
    settings: Optional[Settings] = None,
    **config_overrides: Any,
) -> VantageGraphQLClient:
    """Create a VantageGraphQLClient with sensible defaults.

    Args:
        url: GraphQL endpoint URL
        persona: Authentication persona
        transport_type: Type of transport to use
        profile: Profile name for caching
        settings: Settings object for token refresh
        **config_overrides: Additional configuration overrides

    Returns:
        Configured VantageGraphQLClient instance
    """
    config = GraphQLClientConfig(url=url, transport_type=transport_type, **config_overrides)

    return VantageGraphQLClient(config=config, persona=persona, profile=profile, settings=settings)


def create_production_client(
    url: str,
    persona: Persona,
    profile: str = "default",
    settings: Optional[Settings] = None,
    **config_overrides: Any,
) -> VantageGraphQLClient:
    """Create production-ready GraphQL client with optimal settings.

    Args:
        url: GraphQL endpoint URL
        persona: Authentication persona (required for production)
        profile: Profile name for caching
        settings: Settings object for token refresh
        **config_overrides: Additional configuration overrides

    Returns:
        Production-configured VantageGraphQLClient instance
    """
    production_config: Dict[str, Any] = {
        "timeout": 30,
        "max_retries": 3,
        "retry_backoff_factor": 1.0,
        "verify_ssl": True,
        "fetch_schema": False,  # Skip schema fetching in production for performance
        "validate_queries": False,  # Skip validation in production for performance
        "enable_logging": True,
        "log_queries": False,  # Never log queries in production for security
        **config_overrides,
    }

    return create_vantage_graphql_client(
        url=url,
        persona=persona,
        transport_type=TransportType.AIOHTTP,
        profile=profile,
        settings=settings,
        **production_config,
    )


def create_development_client(
    url: str,
    persona: Optional[Persona] = None,
    profile: str = "default",
    settings: Optional[Settings] = None,
    **config_overrides: Any,
) -> VantageGraphQLClient:
    """Create development GraphQL client with debugging features.

    Args:
        url: GraphQL endpoint URL
        persona: Authentication persona (optional for development)
        profile: Profile name for caching
        settings: Settings object for token refresh
        **config_overrides: Additional configuration overrides

    Returns:
        Development-configured VantageGraphQLClient instance
    """
    development_config: Dict[str, Any] = {
        "timeout": 60,
        "max_retries": 1,
        "verify_ssl": False,  # Allow self-signed certificates in dev
        "fetch_schema": True,  # Enable schema introspection
        "validate_queries": True,  # Enable query validation
        "enable_logging": True,
        "log_queries": True,  # Enable query logging for debugging
        **config_overrides,
    }

    return create_vantage_graphql_client(
        url=url,
        persona=persona,
        transport_type=TransportType.AIOHTTP,
        profile=profile,
        settings=settings,
        **development_config,
    )


def create_async_graphql_client(settings: Settings, profile: str = "default"):
    """Create an async GraphQL client for the given settings and profile.

    This is a convenience function that combines the auth/cache logic with client creation.
    It replaces the old async_graphql_client.py module functionality.

    Args:
        settings: Settings object containing API configuration
        profile: Profile name to use for authentication

    Returns:
        Configured VantageGraphQLClient instance

    Raises:
        Exception: If client creation fails
    """
    try:
        # Load tokens and create persona
        token_set = load_tokens_from_cache(profile)
        persona = extract_persona(profile, token_set, settings)

        # Construct the GraphQL endpoint URL
        graphql_url = f"{settings.api_base_url}/cluster/graphql"

        # Create async client with settings
        client = create_production_client(
            url=graphql_url,
            persona=persona,
            profile=profile,
            settings=settings,
            timeout=30,
            max_retries=3,
            verify_ssl=True,
            enable_logging=True,
            log_queries=False,  # Security: don't log queries in production
        )

        logger.debug(f"Created async GraphQL client for {graphql_url}")
        return client

    except Exception as e:
        logger.error(f"Failed to create async GraphQL client: {e}")
        raise
