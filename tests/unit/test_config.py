"""Tests for the config module."""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import typer
from pydantic import ValidationError

from vantage_cli.config import (
    Settings,
    attach_settings,
    clear_settings,
    dump_settings,
    ensure_default_profile_exists,
    get_active_profile,
    init_settings,
    init_user_filesystem,
    set_active_profile,
)


class TestSettings:
    """Tests for Settings model."""

    def test_settings_default_values(self):
        """Test Settings model with default values."""
        # Execute
        settings = Settings()

        # Verify - check that all expected clouds exist (order doesn't matter)
        expected_clouds = {"localhost", "aws", "gcp", "azure", "on-premises", "k8s", "maas"}
        actual_clouds = set(settings.supported_clouds)
        assert expected_clouds.issubset(actual_clouds), (
            f"Missing clouds: {expected_clouds - actual_clouds}"
        )
        assert settings.api_base_url == "https://apis.vantagecompute.ai"
        assert settings.oidc_base_url == "https://auth.vantagecompute.ai"
        assert settings.oidc_client_id == "default"
        assert settings.oidc_max_poll_time == 300  # 5 * 60

    def test_settings_custom_values(self):
        """Test Settings model with custom values."""
        # Execute
        settings = Settings(
            api_base_url="https://custom.api.com",
            oidc_base_url="https://custom.auth.com",
            oidc_client_id="custom_client",
            oidc_max_poll_time=600,
        )

        # Verify
        assert settings.api_base_url == "https://custom.api.com"
        assert settings.oidc_base_url == "https://custom.auth.com"
        assert settings.oidc_client_id == "custom_client"
        assert settings.oidc_max_poll_time == 600

    def test_oidc_domain_computed_field(self):
        """Test oidc_domain computed field."""
        # Setup
        settings = Settings(oidc_base_url="https://auth.example.com")

        # Execute & Verify
        assert settings.oidc_domain == "auth.example.com"

    def test_oidc_domain_no_protocol(self):
        """Test oidc_domain with URL without protocol."""
        # Setup
        settings = Settings(oidc_base_url="auth.example.com")

        # Execute & Verify
        assert settings.oidc_domain == "auth.example.com"

    def test_oidc_token_url_computed_field(self):
        """Test oidc_token_url computed field."""
        # Setup
        settings = Settings(oidc_base_url="https://auth.example.com")

        # Execute & Verify
        expected_url = "https://auth.example.com/realms/vantage/protocol/openid-connect/token"
        assert settings.oidc_token_url == expected_url


class TestInitUserFilesystem:
    """Tests for init_user_filesystem function."""

    @patch("vantage_cli.config.USER_TOKEN_CACHE_DIR")
    def test_init_user_filesystem_success(self, mock_cache_dir):
        """Test successful user filesystem initialization."""
        # Setup
        mock_profile_dir = Mock()
        mock_cache_dir.__truediv__.return_value = mock_profile_dir

        # Execute
        init_user_filesystem("test_profile")

        # Verify
        mock_cache_dir.__truediv__.assert_called_once_with("test_profile")
        mock_profile_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("vantage_cli.config.USER_TOKEN_CACHE_DIR")
    def test_init_user_filesystem_mkdir_error(self, mock_cache_dir):
        """Test user filesystem initialization with mkdir error."""
        # Setup
        mock_profile_dir = Mock()
        mock_cache_dir.__truediv__.return_value = mock_profile_dir
        mock_profile_dir.mkdir.side_effect = OSError("Permission denied")

        # Execute & Verify
        with pytest.raises(OSError, match="Permission denied"):
            init_user_filesystem("test_profile")


class TestInitSettings:
    """Tests for init_settings function."""

    def test_init_settings_no_values(self):
        """Test init_settings with no values."""
        # Execute
        settings = init_settings()

        # Verify
        assert isinstance(settings, Settings)
        assert settings.oidc_client_id == "default"

    def test_init_settings_with_values(self):
        """Test init_settings with custom values."""
        # Execute
        settings = init_settings(
            api_base_url="https://custom.api.com", oidc_client_id="custom_client"
        )

        # Verify
        assert settings.api_base_url == "https://custom.api.com"
        assert settings.oidc_client_id == "custom_client"

    def test_init_settings_validation_error(self):
        """Test init_settings with invalid values."""
        # Execute & Verify
        with pytest.raises(ValidationError):
            init_settings(oidc_max_poll_time="invalid")  # Should be int


class TestAttachSettings:
    """Tests for attach_settings decorator."""

    def test_attach_settings_decorator_sync(self):
        """Test attach_settings decorator on sync function."""

        # Setup
        @attach_settings
        def test_func(ctx):
            return ctx.obj.settings

        ctx = Mock(spec=typer.Context)
        ctx.obj = Mock()
        ctx.obj.profile = "test_profile"

        with patch("vantage_cli.config.USER_CONFIG_FILE") as mock_config_file:
            mock_config_file.exists.return_value = True
            mock_config_file.read_text.return_value = json.dumps(
                {"test_profile": {"api_base_url": "https://test.com"}}
            )

            # Execute
            result = test_func(ctx)

            # Verify
            assert isinstance(result, Settings)
            assert result.api_base_url == "https://test.com"

    def test_attach_settings_decorator_async(self):
        """Test attach_settings decorator on async function."""

        # Setup
        @attach_settings
        async def async_test_func(ctx):
            return ctx.obj.settings

        ctx = Mock(spec=typer.Context)
        ctx.obj = Mock()
        ctx.obj.profile = "test_profile"

        with patch("vantage_cli.config.USER_CONFIG_FILE") as mock_config_file:
            mock_config_file.exists.return_value = True
            mock_config_file.read_text.return_value = '{"test_profile": {}}'

            # Execute
            result = asyncio.run(async_test_func(ctx))

            # Verify
            assert isinstance(result, Settings)

    def test_attach_settings_no_config_file(self):
        """Test attach_settings when config file doesn't exist."""

        # Setup
        @attach_settings
        def test_func(ctx):
            return ctx.obj.settings

        ctx = Mock(spec=typer.Context)
        ctx.obj = Mock()
        ctx.obj.profile = "test_profile"

        with patch("vantage_cli.config.USER_CONFIG_FILE") as mock_config_file:
            mock_config_file.exists.return_value = False
            mock_config_file.read_text.side_effect = FileNotFoundError()

            # Execute & Verify
            with pytest.raises(typer.Exit):
                test_func(ctx)

    def test_attach_settings_profile_not_in_config(self):
        """Test attach_settings when profile is not in config."""

        # Setup
        @attach_settings
        def test_func(ctx):
            return ctx.obj.settings

        ctx = Mock(spec=typer.Context)
        ctx.obj = Mock()
        ctx.obj.profile = "missing_profile"

        with patch("vantage_cli.config.USER_CONFIG_FILE") as mock_config_file:
            mock_config_file.exists.return_value = True
            mock_config_file.read_text.return_value = json.dumps(
                {"other_profile": {"api_base_url": "https://other.com"}}
            )

            # Execute & Verify
            with pytest.raises(TypeError):
                test_func(ctx)

    def test_attach_settings_json_decode_error(self):
        """Test attach_settings with JSON decode error."""

        # Setup
        @attach_settings
        def test_func(ctx):
            return ctx.obj.settings

        ctx = Mock(spec=typer.Context)
        ctx.obj = Mock()
        ctx.obj.profile = "test_profile"

        with patch("vantage_cli.config.USER_CONFIG_FILE") as mock_config_file:
            mock_config_file.exists.return_value = True
            mock_config_file.read_text.return_value = "invalid json"

            # Execute & Verify
            with pytest.raises(json.JSONDecodeError):
                test_func(ctx)


class TestDumpSettings:
    """Tests for dump_settings function."""

    @patch("vantage_cli.config.USER_CONFIG_FILE")
    def test_dump_settings_new_file(self, mock_config_file):
        """Test dump_settings creating new file."""
        # Setup
        settings = Settings(api_base_url="https://test.com")
        mock_config_file.exists.return_value = False
        mock_config_file.write_text = Mock()

        # Execute
        dump_settings("test_profile", settings)

        # Verify
        # Note: dump_settings doesn't explicitly create parent directory, relies on write_text
        mock_config_file.write_text.assert_called_once()
        # Check JSON content
        written_content = mock_config_file.write_text.call_args[0][0]
        config_data = json.loads(written_content)
        assert "test_profile" in config_data
        assert config_data["test_profile"]["api_base_url"] == "https://test.com"

    @patch("vantage_cli.config.USER_CONFIG_FILE")
    def test_dump_settings_existing_file(self, mock_config_file):
        """Test dump_settings updating existing file."""
        # Setup
        settings = Settings(api_base_url="https://test.com")
        mock_config_file.exists.return_value = True
        mock_config_file.read_text.return_value = json.dumps(
            {"existing_profile": {"api_base_url": "https://existing.com"}}
        )
        mock_config_file.write_text = Mock()

        # Execute
        dump_settings("test_profile", settings)

        # Verify
        mock_config_file.write_text.assert_called_once()
        written_content = mock_config_file.write_text.call_args[0][0]
        config_data = json.loads(written_content)
        assert "existing_profile" in config_data
        assert "test_profile" in config_data
        assert config_data["test_profile"]["api_base_url"] == "https://test.com"


class TestClearSettings:
    """Tests for clear_settings function."""

    @patch("vantage_cli.config.VANTAGE_CLI_LOCAL_USER_BASE_DIR")
    def test_clear_settings_success(self, mock_base_dir):
        """Test successful settings clearing."""
        with patch("shutil.rmtree") as mock_rmtree:
            # Execute
            clear_settings()

            # Verify
            mock_rmtree.assert_called_once_with(mock_base_dir)

    @patch("vantage_cli.config.VANTAGE_CLI_LOCAL_USER_BASE_DIR")
    def test_clear_settings_no_directory(self, mock_base_dir):
        """Test clear_settings when directory doesn't exist."""
        with patch("shutil.rmtree") as mock_rmtree:
            # Configure mock to raise FileNotFoundError
            mock_rmtree.side_effect = FileNotFoundError()

            # Execute (should not raise an exception)
            clear_settings()

            # Verify - rmtree should be called on base directory
            mock_rmtree.assert_called_once_with(mock_base_dir)


class TestEnsureDefaultProfileExists:
    """Tests for ensure_default_profile_exists function."""

    @patch("vantage_cli.config.USER_CONFIG_FILE")
    @patch("vantage_cli.config.dump_settings")
    def test_ensure_default_profile_new_config(
        self, mock_dump, mock_config_file, isolated_vantage_home
    ):
        """Test ensure_default_profile_exists with new config file."""
        # Setup
        mock_config_file.exists.return_value = False

        # Execute
        ensure_default_profile_exists()

        # Verify
        mock_dump.assert_called_once()
        # Check that default settings are dumped
        call_args = mock_dump.call_args
        assert call_args[0][0] == "default"
        assert isinstance(call_args[0][1], Settings)

    @patch("vantage_cli.config.USER_CONFIG_FILE")
    @patch("vantage_cli.config.dump_settings")
    def test_ensure_default_profile_existing_config_no_default(
        self, mock_dump, mock_config_file, isolated_vantage_home
    ):
        """Test ensure_default_profile_exists with existing config but no default profile."""
        # Setup - config file exists, so dump_settings shouldn't be called
        mock_config_file.exists.return_value = True
        mock_config_file.read_text.return_value = json.dumps(
            {"other_profile": {"api_base_url": "https://other.com"}}
        )

        # Execute
        ensure_default_profile_exists()

        # Verify - function only creates directory if needed, doesn't create default profile if config exists
        mock_dump.assert_not_called()  # No dump since config file already exists

    @patch("vantage_cli.config.USER_CONFIG_FILE")
    @patch("vantage_cli.config.dump_settings")
    def test_ensure_default_profile_already_exists(
        self, mock_dump, mock_config_file, isolated_vantage_home
    ):
        """Test ensure_default_profile_exists when default profile already exists."""
        # Setup
        mock_config_file.exists.return_value = True
        mock_config_file.read_text.return_value = json.dumps(
            {"default": {"api_base_url": "https://default.com"}}
        )

        # Execute
        ensure_default_profile_exists()

        # Verify - nothing should be called since everything exists
        mock_dump.assert_not_called()


class TestGetActiveProfile:
    """Tests for get_active_profile function."""

    @patch("vantage_cli.config.VANTAGE_CLI_ACTIVE_PROFILE")
    def test_get_active_profile_exists(self, mock_active_file):
        """Test get_active_profile when active profile file exists."""
        # Setup
        mock_active_file.exists.return_value = True
        mock_active_file.read_text.return_value = "custom_profile"

        # Execute
        result = get_active_profile()

        # Verify
        assert result == "custom_profile"

    @patch("vantage_cli.config.VANTAGE_CLI_ACTIVE_PROFILE")
    def test_get_active_profile_not_exists(self, mock_active_file):
        """Test get_active_profile when active profile file doesn't exist."""
        # Setup
        mock_active_file.exists.return_value = False

        # Execute
        result = get_active_profile()

        # Verify
        assert result == "default"

    @patch("vantage_cli.config.VANTAGE_CLI_ACTIVE_PROFILE")
    def test_get_active_profile_read_error(self, mock_active_file):
        """Test get_active_profile when reading file fails."""
        # Setup
        mock_active_file.exists.return_value = True
        mock_active_file.read_text.side_effect = PermissionError("Permission denied")

        # Execute
        result = get_active_profile()

        # Verify - should return default on read error
        assert result == "default"


class TestSetActiveProfile:
    """Tests for set_active_profile function."""

    @patch("vantage_cli.config.VANTAGE_CLI_ACTIVE_PROFILE")
    def test_set_active_profile_success(self, mock_active_file):
        """Test successful set_active_profile."""
        # Setup
        mock_active_file.parent.mkdir = Mock()

        # Execute
        set_active_profile("custom_profile")

        # Verify
        mock_active_file.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_active_file.write_text.assert_called_once_with("custom_profile")

    @patch("vantage_cli.config.VANTAGE_CLI_ACTIVE_PROFILE")
    def test_set_active_profile_mkdir_error(self, mock_active_file):
        """Test set_active_profile with mkdir error."""
        # Setup
        mock_active_file.parent.mkdir.side_effect = OSError("Permission denied")

        # Execute & Verify
        with pytest.raises(OSError, match="Permission denied"):
            set_active_profile("custom_profile")

    @patch("vantage_cli.config.VANTAGE_CLI_ACTIVE_PROFILE")
    def test_set_active_profile_write_error(self, mock_active_file):
        """Test set_active_profile with write error."""
        # Setup
        mock_active_file.parent.mkdir = Mock()
        mock_active_file.write_text.side_effect = OSError("Write error")

        # Execute & Verify
        with pytest.raises(OSError, match="Write error"):
            set_active_profile("custom_profile")


class TestIntegration:
    """Integration tests for config module."""

    def test_settings_roundtrip(self):
        """Test settings can be dumped and loaded correctly."""
        # Setup
        original_settings = Settings(
            api_base_url="https://test.com", oidc_client_id="test_client", oidc_max_poll_time=600
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"

            with patch("vantage_cli.config.USER_CONFIG_FILE", config_file):
                # Execute dump
                dump_settings("test_profile", original_settings)

                # Execute load through attach_settings
                @attach_settings
                def load_settings(ctx):
                    return ctx.obj.settings

                ctx = Mock(spec=typer.Context)
                ctx.obj = Mock()
                ctx.obj.profile = "test_profile"

                loaded_settings = load_settings(ctx)

                # Verify
                assert loaded_settings.api_base_url == original_settings.api_base_url
                assert loaded_settings.oidc_client_id == original_settings.oidc_client_id
                assert loaded_settings.oidc_max_poll_time == original_settings.oidc_max_poll_time

    def test_profile_management_flow(self, isolated_vantage_home):
        """Test complete profile setup and management flow."""
        active_file = isolated_vantage_home / "active_profile"

        with patch("vantage_cli.config.VANTAGE_CLI_ACTIVE_PROFILE", active_file):
            # Test initial state
            assert get_active_profile() == "default"

            # Test setting active profile
            set_active_profile("custom_profile")
            assert get_active_profile() == "custom_profile"

            # Test file persistence
            assert active_file.read_text() == "custom_profile"
