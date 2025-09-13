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
"""Tests for the auth module."""

import json
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from jose import ExpiredSignatureError
from typer import Context

from vantage_cli.auth import (
    extract_persona,
    fetch_auth_tokens,
    init_persona,
    is_token_expired,
    refresh_access_token,
    refresh_access_token_standalone,
    refresh_token_if_needed,
    validate_token_and_extract_identity,
)
from vantage_cli.exceptions import Abort
from vantage_cli.schemas import CliContext, DeviceCodeData, IdentityData, Persona, TokenSet


class TestExtractPersona:
    """Tests for extract_persona function."""

    @patch("vantage_cli.auth.refresh_token_if_needed")
    @patch("vantage_cli.auth.validate_token_and_extract_identity")
    @patch("vantage_cli.auth.save_tokens_to_cache")
    def test_extract_persona_success(self, mock_save, mock_validate, mock_refresh):
        """Test successful persona extraction."""
        # Setup
        token_set = TokenSet(access_token="test_token")
        identity_data = IdentityData(email="test@example.com", client_id="test_client")
        mock_refresh.return_value = token_set
        mock_validate.return_value = identity_data

        # Execute
        result = extract_persona("test_profile", token_set)

        # Verify
        assert isinstance(result, Persona)
        assert result.token_set == token_set
        assert result.identity_data == identity_data
        mock_refresh.assert_called_once_with("test_profile", token_set)
        mock_validate.assert_called_once_with(token_set)
        mock_save.assert_called_once_with("test_profile", token_set)

    @patch("vantage_cli.auth.load_tokens_from_cache")
    @patch("vantage_cli.auth.refresh_token_if_needed")
    @patch("vantage_cli.auth.validate_token_and_extract_identity")
    @patch("vantage_cli.auth.save_tokens_to_cache")
    def test_extract_persona_load_from_cache(
        self, mock_save, mock_validate, mock_refresh, mock_load
    ):
        """Test persona extraction loading from cache."""
        # Setup
        cached_token_set = TokenSet(access_token="cached_token")
        identity_data = IdentityData(email="test@example.com", client_id="test_client")
        mock_load.return_value = cached_token_set
        mock_refresh.return_value = cached_token_set
        mock_validate.return_value = identity_data

        # Execute
        result = extract_persona("test_profile")

        # Verify
        assert isinstance(result, Persona)
        mock_load.assert_called_once_with("test_profile")
        mock_refresh.assert_called_once_with("test_profile", cached_token_set)
        mock_validate.assert_called_once_with(cached_token_set)

    @patch("vantage_cli.auth.refresh_token_if_needed")
    @patch("vantage_cli.auth.validate_token_and_extract_identity")
    def test_extract_persona_validation_error(self, mock_validate, mock_refresh):
        """Test persona extraction when validation fails."""
        # Setup
        token_set = TokenSet(access_token="invalid_token")
        mock_refresh.return_value = token_set
        mock_validate.side_effect = ExpiredSignatureError("Token expired")

        # Execute & Verify
        with pytest.raises(ExpiredSignatureError):
            extract_persona("test_profile", token_set)


class TestValidateTokenAndExtractIdentity:
    """Tests for validate_token_and_extract_identity function."""

    @patch("vantage_cli.auth.jwt.decode")
    def test_validate_token_success(self, mock_decode):
        """Test successful token validation and identity extraction."""
        # Setup
        token_set = TokenSet(access_token="valid_token")
        mock_decode.return_value = {"email": "test@example.com", "azp": "test_client"}

        # Execute
        result = validate_token_and_extract_identity(token_set)

        # Verify
        assert isinstance(result, IdentityData)
        assert result.email == "test@example.com"
        assert result.client_id == "test_client"
        mock_decode.assert_called_once_with(
            "valid_token",
            "",
            options={
                "verify_signature": False,
                "verify_aud": False,
                "verify_exp": True,
            },
        )

    @patch("vantage_cli.auth.jwt.decode")
    def test_validate_token_no_access_token(self, mock_decode):
        """Test validation with no access token."""
        # Setup
        token_set = TokenSet(access_token="")  # Empty string for no access token

        # Execute & Verify
        with pytest.raises(Abort) as exc_info:
            validate_token_and_extract_identity(token_set)

        assert "Access token file exists but it is empty" in str(exc_info.value)
        mock_decode.assert_not_called()

    @patch("vantage_cli.auth.jwt.decode")
    def test_validate_token_expired_signature(self, mock_decode):
        """Test validation with expired token signature."""
        # Setup
        token_set = TokenSet(access_token="expired_token")
        mock_decode.side_effect = ExpiredSignatureError("Token expired")

        # Execute & Verify
        with pytest.raises(ExpiredSignatureError):
            validate_token_and_extract_identity(token_set)

    @patch("vantage_cli.auth.jwt.decode")
    def test_validate_token_decode_error(self, mock_decode):
        """Test validation with JWT decode error."""
        # Setup
        token_set = TokenSet(access_token="invalid_token")
        mock_decode.side_effect = Exception("Invalid JWT")

        # Execute & Verify
        with pytest.raises(Abort) as exc_info:
            validate_token_and_extract_identity(token_set)

        assert "There was an unknown error while validating the access token" in str(
            exc_info.value
        )

    @patch("vantage_cli.auth.jwt.decode")
    def test_validate_token_missing_email(self, mock_decode):
        """Test validation with missing email in token."""
        # Setup
        token_set = TokenSet(access_token="token_no_email")
        mock_decode.return_value = {"azp": "test_client"}

        # Execute - this should succeed as email is optional
        result = validate_token_and_extract_identity(token_set)

        # Verify
        assert result.client_id == "test_client"
        assert result.email is None

    @patch("vantage_cli.auth.jwt.decode")
    def test_validate_token_missing_client_id(self, mock_decode):
        """Test validation with missing client_id (azp) in token."""
        # Setup
        token_set = TokenSet(access_token="token_no_client")
        mock_decode.return_value = {"email": "test@example.com"}

        # Execute - this should succeed with client_id defaulting to "unknown"
        result = validate_token_and_extract_identity(token_set)

        # Verify
        assert result.client_id == "unknown"
        assert result.email == "test@example.com"


class TestIsTokenExpired:
    """Tests for is_token_expired function."""

    @patch("vantage_cli.auth.jwt.decode")
    def test_token_not_expired(self, mock_decode):
        """Test token that is not expired."""
        # Setup - token expires in 3600 seconds (1 hour from now)
        import time

        future_exp = int(time.time()) + 3600
        mock_decode.return_value = {"exp": future_exp}

        # Execute
        result = is_token_expired("valid_token")

        # Verify
        assert result is False
        mock_decode.assert_called_once_with(
            "valid_token",
            "",
            options={"verify_signature": False, "verify_aud": False, "verify_exp": False},
        )

    @patch("vantage_cli.auth.jwt.decode")
    def test_token_expired(self, mock_decode):
        """Test token that is expired."""
        # Setup - token expired 1 hour ago
        import time

        past_exp = int(time.time()) - 3600
        mock_decode.return_value = {"exp": past_exp}

        # Execute
        result = is_token_expired("expired_token")

        # Verify
        assert result is True
        mock_decode.assert_called_once_with(
            "expired_token",
            "",
            options={"verify_signature": False, "verify_aud": False, "verify_exp": False},
        )

    @patch("vantage_cli.auth.jwt.decode")
    def test_token_expired_with_buffer(self, mock_decode):
        """Test token expiration with buffer time."""
        # Setup - token expires in 30 seconds, but buffer is 60 seconds
        import time

        soon_exp = int(time.time()) + 30
        mock_decode.return_value = {"exp": soon_exp}

        # Execute
        result = is_token_expired("token", buffer_seconds=60)

        # Verify
        assert result is True  # Should be considered expired due to buffer

    @patch("vantage_cli.auth.jwt.decode")
    def test_token_no_exp_claim(self, mock_decode):
        """Test token without exp claim."""
        # Setup
        mock_decode.return_value = {"email": "test@example.com"}

        # Execute
        result = is_token_expired("token_no_exp")

        # Verify
        assert result is True  # Should be considered expired

    @patch("vantage_cli.auth.jwt.decode")
    @patch("vantage_cli.auth.logger")
    def test_token_decode_error(self, mock_logger, mock_decode):
        """Test token decode error."""
        # Setup
        mock_decode.side_effect = Exception("Decode error")

        # Execute
        result = is_token_expired("invalid_token")

        # Verify
        assert result is True  # Should be considered expired on error
        mock_logger.debug.assert_called_once()


class TestRefreshTokenIfNeeded:
    """Tests for refresh_token_if_needed function."""

    @patch("vantage_cli.auth.is_token_expired")
    def test_no_access_token(self, mock_expired):
        """Test when no access token is available."""
        # Setup
        token_set = TokenSet(access_token="")  # Empty string means no access token

        # Execute
        result = refresh_token_if_needed("test_profile", token_set)

        # Verify
        assert result == token_set
        mock_expired.assert_not_called()

    @patch("vantage_cli.auth.is_token_expired")
    def test_token_not_expired(self, mock_expired):
        """Test when token is not expired."""
        # Setup
        token_set = TokenSet(access_token="valid_token")
        mock_expired.return_value = False

        # Execute
        result = refresh_token_if_needed("test_profile", token_set)

        # Verify
        assert result == token_set
        mock_expired.assert_called_once_with("valid_token")

    @patch("vantage_cli.auth.is_token_expired")
    def test_token_expired_no_refresh_token(self, mock_expired):
        """Test when token is expired but no refresh token available."""
        # Setup
        token_set = TokenSet(access_token="expired_token")
        mock_expired.return_value = True

        # Execute & Verify
        with pytest.raises(Abort) as exc_info:
            refresh_token_if_needed("test_profile", token_set)

        assert "no refresh token is available" in str(exc_info.value)

    @patch("vantage_cli.auth.is_token_expired")
    @patch("vantage_cli.auth.refresh_access_token_standalone")
    @patch("vantage_cli.auth.save_tokens_to_cache")
    @patch("vantage_cli.auth.USER_CONFIG_FILE")
    def test_successful_refresh(self, mock_config_file, mock_save, mock_refresh, mock_expired):
        """Test successful token refresh."""
        # Setup
        token_set = TokenSet(access_token="expired_token", refresh_token="refresh_token")
        mock_expired.return_value = True
        mock_refresh.return_value = True
        mock_config_file.exists.return_value = True
        mock_config_file.read_text.return_value = json.dumps(
            {"test_profile": {"oidc_base_url": "https://test.com"}}
        )

        # Execute
        result = refresh_token_if_needed("test_profile", token_set)

        # Verify
        assert result == token_set
        mock_refresh.assert_called_once()
        mock_save.assert_called_once_with("test_profile", token_set)

    @patch("vantage_cli.auth.is_token_expired")
    @patch("vantage_cli.auth.refresh_access_token_standalone")
    @patch("vantage_cli.auth.USER_CONFIG_FILE")
    def test_refresh_failure(self, mock_config_file, mock_refresh, mock_expired):
        """Test token refresh failure."""
        # Setup
        token_set = TokenSet(access_token="expired_token", refresh_token="refresh_token")
        mock_expired.return_value = True
        mock_refresh.return_value = False
        mock_config_file.exists.return_value = False

        # Execute & Verify
        with pytest.raises(Abort) as exc_info:
            refresh_token_if_needed("test_profile", token_set)

        assert "Failed to refresh the expired access token" in str(exc_info.value)


class TestInitPersona:
    """Tests for init_persona function."""

    @patch("vantage_cli.auth.load_tokens_from_cache")
    @patch("vantage_cli.auth.validate_token_and_extract_identity")
    @patch("vantage_cli.auth.save_tokens_to_cache")
    def test_init_persona_with_provided_token(self, mock_save, mock_validate, mock_load):
        """Test init_persona with provided token set."""
        # Setup
        ctx = Mock(spec=Context)
        ctx.obj = Mock()
        ctx.obj.profile = "test_profile"

        token_set = TokenSet(access_token="test_token")
        identity_data = IdentityData(email="test@example.com", client_id="test_client")
        mock_validate.return_value = identity_data

        # Execute
        result = init_persona(ctx, token_set)

        # Verify
        assert isinstance(result, Persona)
        assert result.token_set == token_set
        assert result.identity_data == identity_data
        mock_load.assert_not_called()
        mock_save.assert_called_once_with("test_profile", token_set)

    @patch("vantage_cli.auth.load_tokens_from_cache")
    @patch("vantage_cli.auth.validate_token_and_extract_identity")
    @patch("vantage_cli.auth.save_tokens_to_cache")
    def test_init_persona_load_from_cache(self, mock_save, mock_validate, mock_load):
        """Test init_persona loading from cache."""
        # Setup
        ctx = Mock(spec=Context)
        ctx.obj = Mock()
        ctx.obj.profile = "test_profile"

        token_set = TokenSet(access_token="cached_token")
        identity_data = IdentityData(email="test@example.com", client_id="test_client")
        mock_load.return_value = token_set
        mock_validate.return_value = identity_data

        # Execute
        result = init_persona(ctx)

        # Verify
        assert isinstance(result, Persona)
        mock_load.assert_called_once_with(profile="test_profile")
        mock_save.assert_called_once_with("test_profile", token_set)

    @patch("vantage_cli.auth.load_tokens_from_cache")
    @patch("vantage_cli.auth.validate_token_and_extract_identity")
    @patch("vantage_cli.auth.refresh_access_token_standalone")
    @patch("vantage_cli.auth.save_tokens_to_cache")
    def test_init_persona_expired_token_refresh_success(
        self, mock_save, mock_refresh, mock_validate, mock_load
    ):
        """Test init_persona with expired token that refreshes successfully."""
        # Setup
        ctx = Mock(spec=Context)
        ctx.obj = Mock()
        ctx.obj.profile = "test_profile"
        ctx.obj.settings = None

        token_set = TokenSet(access_token="expired_token", refresh_token="refresh_token")
        identity_data = IdentityData(email="test@example.com", client_id="test_client")

        mock_load.return_value = token_set
        mock_validate.side_effect = [ExpiredSignatureError("Token expired"), identity_data]
        mock_refresh.return_value = True

        # Execute
        result = init_persona(ctx)

        # Verify
        assert isinstance(result, Persona)
        mock_refresh.assert_called_once()
        assert mock_validate.call_count == 2

    @patch("vantage_cli.auth.load_tokens_from_cache")
    @patch("vantage_cli.auth.validate_token_and_extract_identity")
    def test_init_persona_expired_no_refresh_token(self, mock_validate, mock_load):
        """Test init_persona with expired token and no refresh token."""
        # Setup
        ctx = Mock(spec=Context)
        ctx.obj = Mock()
        ctx.obj.profile = "test_profile"

        token_set = TokenSet(access_token="expired_token")
        mock_load.return_value = token_set
        mock_validate.side_effect = ExpiredSignatureError("Token expired")

        # Execute & Verify
        with pytest.raises(Abort):
            init_persona(ctx)


class TestRefreshAccessTokenStandalone:
    """Tests for refresh_access_token_standalone function."""

    def test_no_refresh_token(self):
        """Test refresh when no refresh token is available."""
        # Setup
        token_set = TokenSet(access_token="token")
        settings = Mock()

        # Execute
        result = refresh_access_token_standalone(token_set, settings)

        # Verify
        assert result is False

    @patch("httpx.Client")
    def test_successful_refresh(self, mock_client_class):
        """Test successful token refresh."""
        # Setup
        token_set = TokenSet(access_token="old_token", refresh_token="refresh_token")
        settings = Mock()
        settings.oidc_base_url = "https://auth.example.com"
        settings.oidc_client_id = "test_client"

        mock_client = Mock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
        }
        mock_client.post.return_value = mock_response

        # Execute
        result = refresh_access_token_standalone(token_set, settings)

        # Verify
        assert result is True
        assert token_set.access_token == "new_access_token"
        assert token_set.refresh_token == "new_refresh_token"
        mock_client.post.assert_called_once()

    @patch("vantage_cli.auth.httpx.Client")
    @patch("vantage_cli.auth.logger")
    def test_refresh_http_error(self, mock_logger, mock_client_class):
        """Test token refresh with HTTP error."""
        # Setup
        token_set = TokenSet(access_token="old_token", refresh_token="refresh_token")
        settings = Mock()
        settings.oidc_base_url = "https://auth.example.com"
        settings.oidc_client_id = "test_client"

        mock_client = Mock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client.post.side_effect = httpx.HTTPError("Network error")

        # Execute
        result = refresh_access_token_standalone(token_set, settings)

        # Verify
        assert result is False
        mock_logger.error.assert_called_once()


class TestRefreshAccessToken:
    """Tests for refresh_access_token async function."""

    @pytest.mark.asyncio
    async def test_refresh_success(self):
        """Test successful async token refresh."""
        # Setup
        ctx = Mock(spec=CliContext)
        ctx.client = Mock()
        ctx.settings = Mock()
        ctx.settings.oidc_client_id = "test_client"

        token_set = TokenSet(access_token="old_token", refresh_token="refresh_token")
        new_token_set = TokenSet(access_token="new_token")

        with patch("vantage_cli.auth.make_oauth_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = new_token_set

            # Execute
            await refresh_access_token(ctx, token_set)

            # Verify
            assert token_set.access_token == "new_token"
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_no_client(self):
        """Test refresh with no HTTP client."""
        # Setup
        ctx = Mock(spec=CliContext)
        ctx.client = None
        token_set = TokenSet(access_token="test_token")

        # Execute & Verify
        with pytest.raises(RuntimeError, match="HTTP client not initialized"):
            await refresh_access_token(ctx, token_set)

    @pytest.mark.asyncio
    async def test_refresh_no_settings(self):
        """Test refresh with no settings."""
        # Setup
        ctx = Mock(spec=CliContext)
        ctx.client = Mock()
        ctx.settings = None
        token_set = TokenSet(access_token="token")

        # Execute & Verify
        with pytest.raises(RuntimeError, match="Settings not initialized"):
            await refresh_access_token(ctx, token_set)


class TestFetchAuthTokens:
    """Tests for fetch_auth_tokens async function."""

    @pytest.mark.asyncio
    async def test_fetch_tokens_success(self):
        """Test successful token fetching."""
        # Setup
        ctx = Mock(spec=CliContext)
        ctx.client = Mock()
        ctx.settings = Mock()
        ctx.settings.oidc_client_id = "test_client"
        ctx.settings.oidc_max_poll_time = 60

        device_code_data = DeviceCodeData(
            device_code="device123",
            user_code="USER123",
            verification_uri="https://auth.example.com/device",
            verification_uri_complete="https://auth.example.com/device?code=USER123",
            expires_in=300,
            interval=5,
        )

        token_set = TokenSet(access_token="new_token")

        with patch("vantage_cli.auth.make_oauth_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [device_code_data, token_set]

            with patch("vantage_cli.auth.terminal_message") as mock_terminal:
                with patch("vantage_cli.auth.TimeLoop") as mock_time_loop:
                    # Mock a single iteration that succeeds
                    mock_tick = Mock()
                    mock_tick.counter = 1
                    mock_time_loop.return_value = [mock_tick]

                    # Execute
                    result = await fetch_auth_tokens(ctx)

                    # Verify
                    assert result == token_set
                    assert mock_request.call_count == 2
                    mock_terminal.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_tokens_no_client(self):
        """Test fetch tokens with no HTTP client."""
        # Setup
        ctx = Mock(spec=CliContext)
        ctx.client = None

        # Execute & Verify
        with pytest.raises(RuntimeError, match="HTTP client not initialized"):
            await fetch_auth_tokens(ctx)

    @pytest.mark.asyncio
    async def test_fetch_tokens_authorization_pending(self):
        """Test fetch tokens with authorization pending - simulates delayed token return."""
        # Setup
        ctx = Mock(spec=CliContext)
        ctx.client = AsyncMock()
        ctx.settings = Mock()
        ctx.settings.oidc_client_id = "vantage-cli"
        ctx.settings.oidc_max_poll_time = 60
        ctx.settings.oidc_base_url = "https://auth.vantagecompute.ai"

        # Use realistic device code data matching the actual service
        device_code_data = DeviceCodeData(
            device_code="device_abc123xyz",
            verification_uri_complete="https://auth.vantagecompute.ai/realms/vantage/device?user_code=ZEVN-VVRH",
            interval=5,
        )

        # Final token set that will be returned after the delay
        final_token_set = TokenSet(
            access_token="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
            refresh_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        )

        with patch("vantage_cli.auth.make_oauth_request", new_callable=AsyncMock) as mock_request:
            # Mock the oauth request sequence:
            # 1. First call: returns device code data
            # 2. Second call: raises exception (will trigger raw HTTP call)
            # 3. Third call: raises exception again (more pending)
            # 4. Fourth call: returns successful token set
            mock_request.side_effect = [
                device_code_data,  # Device code request succeeds
                Exception("Pending"),  # First token request fails
                Exception("Pending"),  # Second token request fails
                final_token_set,  # Third token request succeeds
            ]

            # Mock the raw HTTP responses for authorization_pending
            pending_response = Mock()
            pending_response.json.return_value = {"error": "authorization_pending"}

            # Mock ctx.client.post to return pending responses during polling
            ctx.client.post.side_effect = [
                pending_response,  # First polling attempt
                pending_response,  # Second polling attempt
                # Third attempt will go through make_oauth_request and succeed
            ]

            with patch("vantage_cli.auth.terminal_message") as mock_terminal:
                with patch("vantage_cli.auth.TimeLoop") as mock_time_loop:
                    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                        # Mock three iterations: two pending, one success
                        mock_tick1 = Mock()
                        mock_tick1.counter = 1
                        mock_tick2 = Mock()
                        mock_tick2.counter = 2
                        mock_tick3 = Mock()
                        mock_tick3.counter = 3
                        mock_time_loop.return_value = [mock_tick1, mock_tick2, mock_tick3]

                        # Execute
                        result = await fetch_auth_tokens(ctx)

                        # Verify
                        assert result == final_token_set
                        # Should have called sleep twice (5 second intervals)
                        assert mock_sleep.call_count == 2
                        mock_sleep.assert_called_with(5)  # device_code_data.interval

                        # Verify terminal message was shown with correct URL
                        mock_terminal.assert_called_once()
                        terminal_call_args = mock_terminal.call_args[0][0]
                        assert (
                            "https://auth.vantagecompute.ai/realms/vantage/device?user_code=ZEVN-VVRH"
                            in terminal_call_args
                        )

    @pytest.mark.asyncio
    async def test_fetch_tokens_timeout(self):
        """Test fetch tokens timeout."""
        # Setup
        ctx = Mock(spec=CliContext)
        ctx.client = AsyncMock()
        ctx.settings = Mock()
        ctx.settings.oidc_client_id = "test_client"
        ctx.settings.oidc_max_poll_time = 60
        ctx.settings.oidc_base_url = "https://auth.example.com"

        device_code_data = DeviceCodeData(
            device_code="device123",
            verification_uri_complete="https://auth.example.com/device?code=USER123",
            interval=2,
        )

        with patch("vantage_cli.auth.make_oauth_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [device_code_data, Exception("Pending")]

            # Mock the raw response for authorization_pending
            mock_response = Mock()
            mock_response.json.return_value = {"error": "authorization_pending"}
            ctx.client.post.return_value = mock_response

            with patch("vantage_cli.auth.terminal_message"):
                with patch("vantage_cli.auth.TimeLoop") as mock_time_loop:
                    with patch("asyncio.sleep", new_callable=AsyncMock):
                        # Mock iterations that never succeed (timeout)
                        mock_time_loop.return_value = []  # Empty iterator = timeout

                        # Execute & Verify
                        with pytest.raises(Abort, match="Login process was not completed in time"):
                            await fetch_auth_tokens(ctx)
