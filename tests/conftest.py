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

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

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
def cluster_data():
    """Mock cluster data for testing app deployments."""
    return {
        "name": "test-cluster",
        "clientId": "test-client",
        "clientSecret": "test-secret",
        "creationParameters": {"cloud": "localhost"},
    }
