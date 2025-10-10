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
"""Test configuration and utilities for Vantage CLI tests.

Test isolation strategy:
1. Create a temporary directory and globally patch VANTAGE_CLI_LOCAL_USER_BASE_DIR
   to point to it for all tests.
2. Write a minimal default profile config and directory structure.
3. Never touch the real ~/.vantage-cli.
4. Tests that need to simulate missing config can still patch USER_CONFIG_FILE explicitly.
"""

from __future__ import annotations

import contextlib
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pendulum
import pytest
from jose import jwt

# Create isolated test directory for all tests
_test_home = Path(tempfile.mkdtemp(prefix="vantage_cli_test_"))

# Set up minimal config structure
(_test_home / "token_cache" / "default").mkdir(parents=True, exist_ok=True)
(_test_home / "active_profile").write_text("default")

_default_config = {
    "default": {
        "supported_clouds": ["localhost", "aws", "gcp", "azure", "on-premises", "k8s"],
        "api_base_url": "https://apis.vantagecompute.ai",
        "oidc_base_url": "https://auth.vantagecompute.ai",
        "tunnel_api_url": "https://tunnel.vantagecompute.ai",
        "oidc_client_id": "default",
        "oidc_max_poll_time": 300,
    }
}
(_test_home / "config.json").write_text(json.dumps(_default_config))


@pytest.fixture(scope="session", autouse=True)
def _global_patch_base_dir():
    """Globally patch VANTAGE_CLI_LOCAL_USER_BASE_DIR for all tests."""
    with patch("vantage_cli.constants.VANTAGE_CLI_LOCAL_USER_BASE_DIR", _test_home):
        with patch("vantage_cli.config.VANTAGE_CLI_LOCAL_USER_BASE_DIR", _test_home):
            with patch("vantage_cli.constants.USER_CONFIG_FILE", _test_home / "config.json"):
                with patch("vantage_cli.config.USER_CONFIG_FILE", _test_home / "config.json"):
                    with patch(
                        "vantage_cli.constants.USER_TOKEN_CACHE_DIR", _test_home / "token_cache"
                    ):
                        with patch(
                            "vantage_cli.config.USER_TOKEN_CACHE_DIR", _test_home / "token_cache"
                        ):
                            with patch(
                                "vantage_cli.constants.VANTAGE_CLI_ACTIVE_PROFILE",
                                _test_home / "active_profile",
                            ):
                                with patch(
                                    "vantage_cli.config.VANTAGE_CLI_ACTIVE_PROFILE",
                                    _test_home / "active_profile",
                                ):
                                    with patch(
                                        "vantage_cli.constants.VANTAGE_CLI_DEPLOYMENTS_CACHE_PATH",
                                        _test_home / "deployments",
                                    ):
                                        yield


@pytest.fixture(scope="session")
def isolated_vantage_home() -> Path:
    """Return the isolated test directory."""
    return _test_home


def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Add custom markers
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    for item in items:
        # Mark all tests in test_*_integration.py as integration tests
        if "integration" in str(item.fspath):
            item.add_marker("integration")
        # Mark all other tests as unit tests
        else:
            item.add_marker("unit")


# Mock settings for testing
class MockSettings:
    """Mock settings for testing."""

    def __init__(self):
        self.api_base_url = "https://apis.test.com"
        self.oidc_base_url = "https://auth.test.com"
        self.tunnel_api_url = "https://tunnel.test.com"
        self.oidc_client_id = "test-client"
        self.oidc_max_poll_time = 300
        self.supported_clouds = ["localhost", "aws", "gcp", "azure"]


# Mock console for testing
class MockConsole:
    """Mock console for testing."""

    def __init__(self):
        """Initialize mock console with Mock objects for tracking calls."""
        self.print = MagicMock()
        self.log = MagicMock()
        self.print_json = MagicMock()
        self.set_live = MagicMock()  # For Rich Live compatibility
        self.show_cursor = MagicMock()  # For Rich console cursor control
        self.push_render_hook = MagicMock()  # For Rich Live integration
        self.pop_render_hook = MagicMock()  # For Rich Live integration
        self.line = MagicMock()  # For Rich line method
        self.is_terminal = True  # Rich console compatibility
        self.is_dumb_terminal = False  # Rich console compatibility
        self.is_jupyter = False  # Rich console compatibility
        self.options = MagicMock()  # Rich console options
        self._live_stack = []  # Required for Rich Live integration

    def clear_live(self):
        """Clear live displays."""
        self._live_stack.clear()

    def __enter__(self):
        """Support context manager protocol for Rich."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Support context manager protocol for Rich."""
        pass


# Enhanced JWT Testing Fixtures


@pytest.fixture
def make_token():
    """Enhanced token builder fixture (inspired by armasec patterns).

    Creates JWT tokens with flexible claims and proper expiration handling.
    """

    def _helper(
        azp: Optional[str] = None,
        email: Optional[str] = None,
        client_id: Optional[str] = None,
        sub: Optional[str] = None,
        iss: Optional[str] = None,
        aud: Optional[str] = None,
        expires: Optional[str] = None,
        algorithm: str = "HS256",
        secret: str = "test-secret-key",
        extra_claims: Optional[dict] = None,
        format_keycloak: bool = False,
    ) -> str:
        """Create a JWT token with flexible claims.

        Args:
            azp: Authorized party (client_id for Keycloak)
            email: User email
            client_id: Client identifier
            sub: Subject identifier
            iss: Issuer
            aud: Audience
            expires: Expiration time (string or timestamp)
            algorithm: JWT algorithm
            secret: Signing secret
            extra_claims: Additional claims to include
            format_keycloak: Format token for Keycloak compatibility

        Returns:
            Encoded JWT token string
        """
        now = datetime.now(timezone.utc)

        # Handle expiration
        if expires:
            if isinstance(expires, str):
                # Parse string date format like "2022-02-16 22:30:00"
                try:
                    expires_dt = pendulum.parse(expires, tz="UTC")
                    exp_timestamp = int(expires_dt.timestamp())
                except Exception:
                    # Fallback to current time + 1 hour
                    exp_timestamp = int(now.timestamp()) + 3600
            else:
                exp_timestamp = expires
        else:
            # Default to 1 hour from now
            exp_timestamp = int(now.timestamp()) + 3600

        # Build base claims
        claims = {
            "iat": int(now.timestamp()),
            "exp": exp_timestamp,
        }

        # Add standard claims if provided
        if sub:
            claims["sub"] = sub
        if iss:
            claims["iss"] = iss
        if aud:
            claims["aud"] = aud
        if email:
            claims["email"] = email

        # Handle client ID / AZP
        if azp:
            claims["azp"] = azp
        elif client_id:
            claims["client_id"] = client_id

        # Add extra claims
        if extra_claims:
            claims.update(extra_claims)

        # Keycloak format adjustments
        if format_keycloak and "permissions" in claims:
            test_client = claims.get("azp") or claims.get("client_id", "test-client")
            claims["azp"] = test_client
            claims["resource_access"] = {
                test_client: {
                    "roles": claims.pop("permissions"),
                }
            }

        return jwt.encode(claims, secret, algorithm=algorithm)

    return _helper


@pytest.fixture
def mock_context():
    """Enhanced mock context (following armasec patterns)."""
    from typer import Context

    # Create mock objects
    mock_obj = MagicMock()
    mock_obj.json_output = False
    mock_obj.verbose = False
    mock_obj.profile = "test-profile"
    mock_obj.console = MockConsole()  # Add console for centralized console approach

    # Create mock context
    mock_ctx = MagicMock(spec=Context)
    mock_ctx.obj = mock_obj

    return mock_ctx


@pytest.fixture
def override_cache_dir(tmp_path, mocker):
    """Override cache directory for isolated testing."""
    # Mock the cache directory constants
    mocker.patch("vantage_cli.cache.USER_CACHE_DIR", tmp_path)
    mocker.patch("vantage_cli.cache.USER_TOKEN_DIR", tmp_path / "tokens")

    # Ensure token directory exists
    token_dir = tmp_path / "tokens"
    token_dir.mkdir(exist_ok=True)

    return tmp_path


@pytest.fixture
def mock_json_bypass():
    """Mock RenderStepOutput.json_bypass for tests that check JSON output.

    This fixture provides a mock for the json_bypass class method that captures
    the data passed to it, allowing tests to verify JSON output without needing
    to check actual console output.
    """
    with patch("vantage_cli.render.RenderStepOutput.json_bypass") as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_subprocess() -> Generator[Dict[str, Any], None, None]:
    """Globally mock all subprocess calls to prevent real commands from running during tests.

    This fixture automatically mocks subprocess.run, subprocess.call, subprocess.check_output,
    and subprocess.Popen to ensure no real system commands are executed during testing.

    Individual tests can override this mock if they need specific subprocess behavior.
    """

    def smart_subprocess_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        """Smart subprocess mock that returns appropriate responses based on command."""
        command_args = args[0] if args else kwargs.get("args", [])

        # Handle microk8s status --format yaml
        if (
            isinstance(command_args, list)
            and len(command_args) >= 3
            and command_args[0] == "microk8s"
            and command_args[1] == "status"
            and "--format" in command_args
            and "yaml" in command_args
        ):
            return subprocess.CompletedProcess(
                args=command_args,
                returncode=0,
                stdout="""microk8s:
  running: true
  version: 1.28.3
addons:
  - name: dns
    status: enabled
  - name: helm3
    status: enabled
  - name: hostpath-storage
    status: enabled
  - name: metallb
    status: enabled
  - name: storage
    status: enabled
  - name: registry
    status: disabled
  - name: ingress
    status: disabled""",
                stderr="",
            )

        # Default successful subprocess result
        final_args: list[str] = (
            command_args if isinstance(command_args, list) else ["mocked_command"]
        )
        return subprocess.CompletedProcess(
            args=final_args, returncode=0, stdout="mocked output", stderr=""
        )

    with (
        patch("subprocess.run", side_effect=smart_subprocess_run) as mock_run,
        patch("subprocess.call", return_value=0) as mock_call,
        patch("subprocess.check_output", return_value=b"mocked output") as mock_check_output,
        patch("subprocess.Popen") as mock_popen,
    ):
        # Configure Popen mock to return a mock process
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "mocked output"
        mock_process.stderr = ""
        mock_process.communicate.return_value = ("mocked output", "")
        mock_process.poll.return_value = 0
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        yield {
            "run": mock_run,
            "call": mock_call,
            "check_output": mock_check_output,
            "popen": mock_popen,
            "process": mock_process,
        }


@pytest.fixture
def cluster_data() -> Dict[str, Any]:
    """Mock cluster data for testing app deployments."""
    return {
        "name": "test-cluster",
        "clientId": "test-client",
        "clientSecret": "test-secret",
        "creationParameters": {"cloud": "localhost"},
    }


# Mock GraphQL Client for preventing real API calls during tests


class MockGraphQLClient:
    """Mock GraphQL client that provides canned responses for common operations."""

    def __init__(self):
        """Initialize mock GraphQL client with default responses."""
        self.execute_async = MagicMock()
        self._setup_default_responses()

    def _setup_default_responses(self):
        """Set up default mock responses for common GraphQL operations."""
        # Default getClusters response
        default_clusters_response = {
            "clusters": {
                "edges": [
                    {
                        "node": {
                            "name": "test-cluster",
                            "status": "RUNNING",
                            "clientId": "test-cluster-0d317c8b-1cfe-423e-a518-57f97fd50c6e",
                            "description": "Test cluster",
                            "ownerEmail": "test@example.com",
                            "provider": "localhost",
                            "cloudAccountId": None,
                            "creationParameters": {"cloud": "localhost"},
                        }
                    }
                ],
                "total": 1,
            }
        }

        # Default createCluster response
        default_create_response = {
            "createCluster": {
                "name": "test-cluster",
                "status": "CREATING",
                "clientId": "test-cluster-123",
                "description": "Test cluster",
            }
        }

        # Default deleteCluster response
        default_delete_response = {"deleteCluster": {"message": "Cluster deleted successfully"}}

        # Configure execute_async to return appropriate responses based on query
        async def mock_execute_async(
            query: Any, variables: Optional[Dict[str, Any]] = None, **kwargs: Any
        ) -> Dict[str, Any]:
            query_str = str(query)

            # Handle getClusters query
            if "getClusters" in query_str or "query getClusters" in query_str:
                return default_clusters_response

            # Handle createCluster mutation
            elif "createCluster" in query_str or "mutation createCluster" in query_str:
                return default_create_response

            # Handle deleteCluster mutation
            elif "deleteCluster" in query_str or "mutation deleteCluster" in query_str:
                return default_delete_response

            # Default fallback response
            else:
                return {"data": {"result": "mocked"}}

        self.execute_async.side_effect = mock_execute_async


@pytest.fixture(autouse=True)
def mock_graphql_client() -> Generator[MockGraphQLClient, None, None]:
    """Globally mock GraphQL client creation to prevent real API calls during tests.

    This fixture automatically patches create_async_graphql_client and related functions
    to return a MockGraphQLClient instead of making real HTTP requests to GraphQL APIs.

    Individual tests can override this mock if they need specific GraphQL behavior.
    """
    mock_client = MockGraphQLClient()

    # Mock the main factory function used throughout the codebase
    with patch("vantage_cli.gql_client.create_async_graphql_client", return_value=mock_client):
        # Also patch any import paths where the factory might be used, but tolerate missing attributes
        optional_patch_targets = [
            "vantage_cli.commands.cluster.create.create_async_graphql_client",
            "vantage_cli.commands.cluster.list.create_async_graphql_client",
            "vantage_cli.commands.cluster.delete.create_async_graphql_client",
            "vantage_cli.commands.cluster.utils.create_async_graphql_client",
        ]

        with contextlib.ExitStack() as patch_stack:
            for target in optional_patch_targets:
                try:
                    patch_stack.enter_context(patch(target, return_value=mock_client))
                except AttributeError:
                    continue

            # Mock httpx AsyncClient used for HTTP requests
            with patch("httpx.AsyncClient") as mock_httpx:
                # Create a proper async context manager
                async def mock_aenter(*args: Any, **kwargs: Any) -> Mock:
                    mock_client = Mock()
                    mock_client.post = AsyncMock()
                    mock_client.get = AsyncMock()
                    return mock_client

                async def mock_aexit_http(*args: Any) -> None:
                    pass

                mock_httpx.return_value.__aenter__ = mock_aenter
                mock_httpx.return_value.__aexit__ = mock_aexit_http
                yield mock_client
