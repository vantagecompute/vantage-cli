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
"""Tests for the main module."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
import typer

from vantage_cli.exceptions import Abort
from vantage_cli.main import (
    _check_existing_login,
    login,
    logout,
    main,
    setup_logging,
    whoami,
)
from vantage_cli.schemas import IdentityData, Persona, TokenSet


@pytest.fixture
def mock_async_environment():
    """Mock environment for async functions in main module."""
    with (
        patch("asyncio.run") as mock_run,
        patch("vantage_cli.config.USER_CONFIG_FILE") as mock_config_file,
    ):
        # Mock config file to exist and have valid content
        mock_config_file.read_text.return_value = '{"test_profile": {"client_id": "test"}}'

        # Mock asyncio.run to call the coroutine directly in the current loop
        async def run_in_current_loop(coro):
            return await coro

        mock_run.side_effect = run_in_current_loop

        yield mock_run, mock_config_file


class TestSetupLogging:
    """Tests for setup_logging function."""

    @patch("vantage_cli.main.logger")
    def test_setup_logging_normal(self, mock_logger):
        """Test logging setup with normal verbosity."""
        # Execute
        setup_logging(verbose=False)

        # Verify
        mock_logger.remove.assert_called_once()
        # When verbose=False, logger.add should NOT be called
        mock_logger.add.assert_not_called()
        mock_logger.debug.assert_called_once_with("Logging initialized")

    @patch("vantage_cli.main.logger")
    def test_setup_logging_verbose(self, mock_logger):
        """Test logging setup with verbose mode."""
        # Execute
        setup_logging(verbose=True)

        # Verify
        mock_logger.remove.assert_called_once()
        mock_logger.add.assert_called_once()
        # Check that the log level is DEBUG
        call_args = mock_logger.add.call_args
        assert "DEBUG" in str(call_args)


class TestMain:
    """Tests for main function (app callback)."""

    @patch("vantage_cli.main.ensure_default_profile_exists")
    @patch("vantage_cli.main.setup_logging")
    @patch("vantage_cli.main.get_active_profile")
    def test_main_callback_default_profile(
        self, mock_get_active, mock_setup_logging, mock_ensure_profile
    ):
        """Test main callback with default profile."""
        # Setup
        ctx = Mock(spec=typer.Context)
        ctx.invoked_subcommand = "login"  # Simulate a subcommand being called
        ctx.obj = SimpleNamespace(profile=None, verbose=False, json_output=False)
        mock_get_active.return_value = "default"

        # Execute
        main(ctx)

        # Verify
        mock_ensure_profile.assert_called_once()
        mock_setup_logging.assert_called_once_with(verbose=False)
        mock_get_active.assert_called_once()
        # The context's CLI context should be set with the active profile
        assert hasattr(ctx, "obj")

    @patch("vantage_cli.main.ensure_default_profile_exists")
    @patch("vantage_cli.main.setup_logging")
    def test_main_callback_custom_profile(self, mock_setup_logging, mock_ensure_profile):
        """Test main callback with custom profile."""
        # Setup
        ctx = Mock(spec=typer.Context)
        ctx.invoked_subcommand = "login"  # Simulate a subcommand being called
        ctx.obj = SimpleNamespace(profile="custom", verbose=True, json_output=False)

        # Execute
        main(ctx)

        # Verify
        mock_ensure_profile.assert_called_once()
        mock_setup_logging.assert_called_once_with(verbose=True)
        assert ctx.obj.profile == "custom"

    @patch("vantage_cli.main.ensure_default_profile_exists")
    @patch("vantage_cli.main.get_active_profile")
    @patch("vantage_cli.main.setup_logging")
    def test_main_callback_active_profile(
        self, mock_setup_logging, mock_get_active, mock_ensure_profile
    ):
        """Test main callback using active profile."""
        # Setup
        ctx = Mock(spec=typer.Context)
        ctx.invoked_subcommand = "login"  # Simulate a subcommand being called
        ctx.obj = SimpleNamespace(profile=None, verbose=False, json_output=False)
        mock_get_active.return_value = "active_profile"

        # Execute
        main(ctx)

        # Verify
        mock_ensure_profile.assert_called_once()
        mock_setup_logging.assert_called_once_with(verbose=False)
        mock_get_active.assert_called_once()
        # The context's CLI context should be set with the active profile
        assert hasattr(ctx, "obj")


class TestCheckExistingLogin:
    """Tests for _check_existing_login function."""

    @patch("vantage_cli.main.extract_persona")
    @patch("vantage_cli.main.load_tokens_from_cache")
    @patch("vantage_cli.main.is_token_expired")
    def test_check_existing_login_valid_token(self, mock_expired, mock_load, mock_extract):
        """Test check existing login with valid token."""
        # Setup
        token_set = TokenSet(access_token="valid_token")
        mock_load.return_value = token_set
        mock_expired.return_value = False

        # Mock persona with email
        mock_persona = Mock()
        mock_persona.identity_data.email = "test@example.com"
        mock_extract.return_value = mock_persona

        # Execute
        result = _check_existing_login("test_profile")

        # Verify
        assert result == "test@example.com"
        mock_load.assert_called_once_with("test_profile")
        mock_expired.assert_called_once_with("valid_token")
        mock_extract.assert_called_once_with("test_profile", token_set)

    @patch("vantage_cli.main.load_tokens_from_cache")
    def test_check_existing_login_no_token(self, mock_load):
        """Test check existing login with no token."""
        # Setup
        token_set = TokenSet(access_token="")
        mock_load.return_value = token_set

        # Execute
        result = _check_existing_login("test_profile")

        # Verify
        assert result is None

    @patch("vantage_cli.main.extract_persona")
    @patch("vantage_cli.main.load_tokens_from_cache")
    @patch("vantage_cli.main.is_token_expired")
    def test_check_existing_login_persona_extract_failure(
        self, mock_expired, mock_load, mock_extract
    ):
        """Test existing login path when persona extraction fails (covers inner except)."""
        # Setup a valid, non-expired token so we reach the inner extraction try/except
        token_set = TokenSet(access_token="valid_token")
        mock_load.return_value = token_set
        mock_expired.return_value = False
        mock_extract.side_effect = Exception("persona boom")

        # Execute
        result = _check_existing_login("test_profile")

        # Verify: persona extraction attempted then failed gracefully returning None
        assert result is None
        mock_load.assert_called_once_with("test_profile")
        mock_expired.assert_called_once_with("valid_token")
        mock_extract.assert_called_once_with("test_profile", token_set)

    @patch("vantage_cli.main.load_tokens_from_cache")
    @patch("vantage_cli.main.is_token_expired")
    def test_check_existing_login_expired_token(self, mock_expired, mock_load):
        """Test check existing login with expired token."""
        # Setup
        token_set = TokenSet(access_token="expired_token")
        mock_load.return_value = token_set
        mock_expired.return_value = True

        # Execute
        result = _check_existing_login("test_profile")

        # Verify
        assert result is None

    @patch("vantage_cli.main.load_tokens_from_cache")
    def test_check_existing_login_exception(self, mock_load):
        """Test check existing login with exception."""
        # Setup
        mock_load.side_effect = Exception("Cache error")

        # Execute
        result = _check_existing_login("test_profile")

        # Verify
        assert result is None


class TestLogin:
    """Tests for login command."""

    @pytest.mark.asyncio
    @patch("vantage_cli.main._check_existing_login")
    @patch("vantage_cli.main.Console")
    async def test_login_already_logged_in(self, mock_console, mock_check, mock_async_environment):
        """Test login when already logged in."""
        # Setup
        ctx = Mock(spec=typer.Context)
        ctx.obj = Mock()
        ctx.obj.profile = "test_profile"
        mock_check.return_value = "test@example.com"

        # Execute
        await login(ctx)

        # Verify
        mock_check.assert_called_once_with("test_profile")
        mock_console.assert_called_once()

    @pytest.mark.asyncio
    @patch("vantage_cli.main._check_existing_login")
    @patch("vantage_cli.main.fetch_auth_tokens")
    @patch("vantage_cli.main.extract_persona")
    @patch("vantage_cli.main.Console")
    async def test_login_success(
        self, mock_console, mock_extract, mock_fetch, mock_check, mock_async_environment
    ):
        """Test successful login."""
        # Setup
        ctx = Mock(spec=typer.Context)
        ctx.obj = Mock()
        ctx.obj.profile = "test_profile"
        mock_check.return_value = None

        token_set = TokenSet(access_token="new_token")
        mock_fetch.return_value = token_set

        persona = Persona(
            token_set=token_set,
            identity_data=IdentityData(email="test@example.com", client_id="test_client"),
        )
        mock_extract.return_value = persona

        # Execute
        await login(ctx)

        # Verify
        mock_check.assert_called_once_with("test_profile")
        mock_fetch.assert_called_once_with(ctx.obj)
        mock_extract.assert_called_once_with("test_profile", token_set)
        mock_console.assert_called_once()

    @pytest.mark.asyncio
    @patch("vantage_cli.main._check_existing_login")
    @patch("vantage_cli.main.fetch_auth_tokens")
    @patch("vantage_cli.main.extract_persona")
    @patch("vantage_cli.main.Console")
    async def test_login_fetch_failure(
        self, mock_console, mock_extract, mock_fetch, mock_check, mock_async_environment
    ):
        """Test login when token fetch fails."""
        # Setup
        ctx = Mock(spec=typer.Context)
        ctx.obj = Mock()
        ctx.obj.profile = "test_profile"
        mock_check.return_value = None
        mock_fetch.side_effect = Exception("Network error")

        # Execute & Verify
        with pytest.raises(Exception, match="Network error"):
            await login(ctx)

        # Verify core functions are called
        mock_check.assert_called_once_with("test_profile")
        mock_fetch.assert_called_once_with(ctx.obj)


class TestLogout:
    """Tests for logout command."""

    @pytest.mark.asyncio
    @patch("vantage_cli.main.clear_token_cache")
    @patch("vantage_cli.main._check_existing_login")
    @patch("vantage_cli.main.Console")
    async def test_logout_success(
        self, mock_console, mock_check, mock_clear, mock_async_environment
    ):
        """Test successful logout."""
        # Setup
        ctx = Mock(spec=typer.Context)
        ctx.obj = Mock()
        ctx.obj.profile = "test_profile"
        mock_check.return_value = "user@example.com"

        # Execute
        await logout(ctx)

        # Verify
        mock_clear.assert_called_once_with("test_profile")
        mock_console.assert_called_once()
        mock_check.assert_called_once_with("test_profile")

    @pytest.mark.asyncio
    @patch("vantage_cli.main.clear_token_cache")
    @patch("vantage_cli.main._check_existing_login")
    async def test_logout_clear_failure(self, mock_check, mock_clear, mock_async_environment):
        """Test logout when cache clear fails."""
        # Setup
        ctx = Mock(spec=typer.Context)
        ctx.obj = Mock()
        ctx.obj.profile = "test_profile"
        mock_check.return_value = None
        mock_clear.side_effect = Exception("Clear error")

        # Execute & Verify
        with pytest.raises(Exception, match="Clear error"):
            await logout(ctx)


class TestWhoami:
    """Tests for whoami command."""

    @pytest.mark.asyncio
    @patch("vantage_cli.main.extract_persona")
    @patch("vantage_cli.main.jwt.decode")
    @patch("vantage_cli.main.print_json")
    async def test_whoami_success(
        self, mock_print_json, mock_decode, mock_extract, mock_async_environment
    ):
        """Test successful whoami command."""
        # Setup
        ctx = Mock(spec=typer.Context)
        ctx.obj = Mock()
        ctx.obj.profile = "test_profile"

        # Mock persona and token data
        identity_data = IdentityData(email="user@example.com", client_id="test_client")
        persona = Persona(
            token_set=TokenSet(access_token="test_token"), identity_data=identity_data
        )
        mock_extract.return_value = persona

        # Mock JWT decode
        mock_decode.return_value = {
            "email": "user@example.com",
            "azp": "test_client",
            "iat": 1640995200,  # 2022-01-01 00:00:00 UTC
            "exp": 1641081600,  # 2022-01-02 00:00:00 UTC
        }

        # Execute
        await whoami(ctx)

        # Verify
        mock_extract.assert_called_once_with("test_profile")
        mock_decode.assert_called_once_with(
            "test_token",
            "",
            options={"verify_signature": False, "verify_aud": False, "verify_exp": False},
        )
        mock_print_json.assert_called_once()

    @pytest.mark.asyncio
    @patch("vantage_cli.main.extract_persona")
    async def test_whoami_extract_failure(self, mock_extract, mock_async_environment):
        """Test whoami when persona extraction fails."""
        # Setup
        ctx = Mock(spec=typer.Context)
        ctx.obj = Mock()
        ctx.obj.profile = "test_profile"
        mock_extract.side_effect = Abort("Token expired")

        # Execute - should complete without raising
        await whoami(ctx)

        # Verify
        mock_extract.assert_called_once_with("test_profile")

    @pytest.mark.asyncio
    @patch("vantage_cli.main.extract_persona")
    @patch("vantage_cli.main.jwt.decode")
    async def test_whoami_jwt_decode_error(
        self, mock_decode, mock_extract, mock_async_environment
    ):
        """Test whoami when JWT decode fails."""
        # Setup
        ctx = Mock(spec=typer.Context)
        ctx.obj = Mock()
        ctx.obj.profile = "test_profile"

        identity_data = IdentityData(email="user@example.com", client_id="test_client")
        persona = Persona(
            token_set=TokenSet(access_token="invalid_token"), identity_data=identity_data
        )
        mock_extract.return_value = persona
        mock_decode.side_effect = Exception("Invalid JWT")

        # Execute - should complete without raising since exceptions are caught
        await whoami(ctx)

        # Verify calls
        mock_extract.assert_called_once_with("test_profile")
        mock_decode.assert_called_once()


class TestIntegration:
    """Integration tests for main module functions."""

    @pytest.mark.asyncio
    @patch("vantage_cli.main._check_existing_login")
    @patch("vantage_cli.main.clear_token_cache")
    @patch("vantage_cli.main.fetch_auth_tokens")
    @patch("vantage_cli.main.extract_persona")
    async def test_login_logout_flow(
        self, mock_extract, mock_fetch, mock_clear, mock_check, mock_async_environment
    ):
        """Test login followed by logout flow."""
        # Setup
        ctx = Mock(spec=typer.Context)
        ctx.obj = Mock()
        ctx.obj.profile = "test_profile"

        # Mock the token and persona for login
        token_set = TokenSet(access_token="test_token")
        persona = Persona(
            token_set=token_set,
            identity_data=IdentityData(email="test@example.com", client_id="test_client"),
        )
        mock_fetch.return_value = token_set
        mock_extract.return_value = persona

        # First call - not logged in, second call - logged in
        mock_check.side_effect = [None, "existing_token"]

        # Execute login (simulate already logged in on second check)
        await login(ctx)
        await logout(ctx)

        # Verify
        mock_clear.assert_called_once_with("test_profile")
        mock_fetch.assert_called_once_with(ctx.obj)
        mock_extract.assert_called_once_with("test_profile", token_set)

    def test_setup_logging_levels(self):
        """Test different logging levels are set correctly."""
        with patch("vantage_cli.main.logger") as mock_logger:
            # Test normal mode - should only remove existing handlers
            setup_logging(verbose=False)
            mock_logger.remove.assert_called_once()
            # In normal mode, logger.add is not called (no handlers added)
            mock_logger.add.assert_not_called()

            mock_logger.reset_mock()

            # Test verbose mode - should remove and add debug handler
            setup_logging(verbose=True)
            mock_logger.remove.assert_called_once()
            mock_logger.add.assert_called_once()
            call_args = mock_logger.add.call_args
            assert "DEBUG" in str(call_args)
