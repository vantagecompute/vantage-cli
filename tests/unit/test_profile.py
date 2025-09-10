"""Unit tests for profile commands."""

import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
import typer

# Import the functions we want to test
try:
    from vantage_cli.commands.profile.crud import (
        create_profile,
        delete_profile,
        get_profile,
        list_profiles,
        use_profile,
    )
    from vantage_cli.config import Settings
    from vantage_cli.exceptions import Abort
except ImportError:
    # Handle import errors during testing
    pytest.skip("Profile module not available", allow_module_level=True)


class TestCreateProfile:
    """Test profile creation functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock typer context."""
        ctx = Mock(spec=typer.Context)
        ctx.obj = SimpleNamespace(profile=None, verbose=False, json_output=False)
        ctx.params = {"json_output": False}
        return ctx

    @pytest.fixture
    def sample_settings(self):
        """Sample settings for testing."""
        return {
            "api_base_url": "https://apis.vantagecompute.ai",
            "oidc_base_url": "https://auth.vantagecompute.ai",
            "oidc_client_id": "default",
            "oidc_max_poll_time": 300,
        }

    @patch("vantage_cli.commands.profile.crud._get_all_profiles")
    @patch("vantage_cli.commands.profile.crud.init_user_filesystem")
    @patch("vantage_cli.commands.profile.crud.dump_settings")
    @patch("vantage_cli.commands.profile.crud.get_effective_json_output")
    @patch("vantage_cli.commands.profile.crud._render_profile_details")
    def test_create_profile_success(
        self,
        mock_render_details,
        mock_json_output,
        mock_dump_settings,
        mock_init_filesystem,
        mock_get_profiles,
        mock_context,
        sample_settings,
    ):
        """Test successful profile creation."""
        # Setup mocks
        mock_get_profiles.return_value = {}  # No existing profiles
        mock_json_output.return_value = False  # Rich output

        # Call the function
        create_profile(
            ctx=mock_context,
            profile_name="test-profile",
            **sample_settings,
        )

        # Verify function calls
        mock_init_filesystem.assert_called_once_with("test-profile")
        mock_dump_settings.assert_called_once()
        mock_render_details.assert_called_once()

        # Verify settings object passed to dump_settings
        args, kwargs = mock_dump_settings.call_args
        assert args[0] == "test-profile"
        settings = args[1]
        assert isinstance(settings, Settings)
        assert settings.api_base_url == sample_settings["api_base_url"]

    @patch("vantage_cli.commands.profile.crud._get_all_profiles")
    @patch("vantage_cli.commands.profile.crud.init_user_filesystem")
    @patch("vantage_cli.commands.profile.crud.dump_settings")
    @patch("vantage_cli.commands.profile.crud.set_active_profile")
    @patch("vantage_cli.commands.profile.crud.get_effective_json_output")
    @patch("vantage_cli.commands.profile.crud._render_profile_details")
    def test_create_profile_with_activation(
        self,
        mock_render_details,
        mock_json_output,
        mock_set_active,
        mock_dump_settings,
        mock_init_filesystem,
        mock_get_profiles,
        mock_context,
        sample_settings,
    ):
        """Test profile creation with activation."""
        # Setup mocks
        mock_get_profiles.return_value = {}
        mock_json_output.return_value = False

        # Call with activate=True
        create_profile(
            ctx=mock_context,
            profile_name="test-profile",
            activate=True,
            **sample_settings,
        )

        # Verify activation was called
        mock_set_active.assert_called_once_with("test-profile")

    @patch("vantage_cli.commands.profile.crud._get_all_profiles")
    @patch("vantage_cli.commands.profile.crud.get_effective_json_output")
    @patch("vantage_cli.commands.profile.crud.print_json")
    def test_create_profile_already_exists_json(
        self,
        mock_print_json,
        mock_json_output,
        mock_get_profiles,
        mock_context,
        sample_settings,
    ):
        """Test creating profile that already exists with JSON output."""
        # Setup mocks
        mock_get_profiles.return_value = {"test-profile": {}}
        mock_json_output.return_value = True

        # Call the function
        create_profile(
            ctx=mock_context,
            profile_name="test-profile",
            **sample_settings,
        )

        # Verify JSON error response
        mock_print_json.assert_called_once()
        result = mock_print_json.call_args[1]["data"]
        assert result["success"] is False
        assert result["profile_name"] == "test-profile"
        assert "already exists" in result["message"]

    @patch("vantage_cli.commands.profile.crud._get_all_profiles")
    @patch("vantage_cli.commands.profile.crud.get_effective_json_output")
    def test_create_profile_already_exists_raises_abort(
        self,
        mock_json_output,
        mock_get_profiles,
        mock_context,
        sample_settings,
    ):
        """Test creating profile that already exists raises Abort."""
        # Setup mocks
        mock_get_profiles.return_value = {"test-profile": {}}
        mock_json_output.return_value = False

        # Call should raise Abort
        with pytest.raises(Abort) as exc_info:
            create_profile(
                ctx=mock_context,
                profile_name="test-profile",
                **sample_settings,
            )

        assert "already exists" in str(exc_info.value)

    @patch("vantage_cli.commands.profile.crud._get_all_profiles")
    @patch("vantage_cli.commands.profile.crud.init_user_filesystem")
    @patch("vantage_cli.commands.profile.crud.dump_settings")
    @patch("vantage_cli.commands.profile.crud.get_effective_json_output")
    @patch("vantage_cli.commands.profile.crud._render_profile_details")
    def test_create_profile_with_force_overwrite(
        self,
        mock_render_details,
        mock_json_output,
        mock_dump_settings,
        mock_init_filesystem,
        mock_get_profiles,
        mock_context,
        sample_settings,
    ):
        """Test creating profile that already exists with force flag."""
        # Setup mocks
        mock_get_profiles.return_value = {"test-profile": {}}
        mock_json_output.return_value = False

        # Call with force=True
        create_profile(
            ctx=mock_context,
            profile_name="test-profile",
            force=True,
            **sample_settings,
        )

        # Should succeed
        mock_init_filesystem.assert_called_once_with("test-profile")
        mock_dump_settings.assert_called_once()


class TestDeleteProfile:
    """Test profile deletion functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock typer context."""
        ctx = Mock(spec=typer.Context)
        ctx.obj = SimpleNamespace(profile=None, verbose=False, json_output=False)
        ctx.params = {"json_output": False}
        return ctx

    @patch("vantage_cli.commands.profile.crud._get_all_profiles")
    @patch("vantage_cli.commands.profile.crud.get_effective_json_output")
    @patch("vantage_cli.commands.profile.crud.print_json")
    def test_delete_nonexistent_profile_json(
        self,
        mock_print_json,
        mock_json_output,
        mock_get_profiles,
        mock_context,
    ):
        """Test deleting non-existent profile with JSON output."""
        # Setup mocks
        mock_get_profiles.return_value = {}
        mock_json_output.return_value = True

        # Call the function
        delete_profile(
            ctx=mock_context,
            profile_name="nonexistent",
        )

        # Verify JSON error response
        mock_print_json.assert_called_once()
        result = mock_print_json.call_args[1]["data"]
        assert result["success"] is False
        assert result["profile_name"] == "nonexistent"
        assert "does not exist" in result["message"]

    @patch("vantage_cli.commands.profile.crud._get_all_profiles")
    @patch("vantage_cli.commands.profile.crud.get_effective_json_output")
    def test_delete_nonexistent_profile_raises_abort(
        self,
        mock_json_output,
        mock_get_profiles,
        mock_context,
    ):
        """Test deleting non-existent profile raises Abort."""
        # Setup mocks
        mock_get_profiles.return_value = {}
        mock_json_output.return_value = False

        # Call should raise Abort
        with pytest.raises(Abort) as exc_info:
            delete_profile(
                ctx=mock_context,
                profile_name="nonexistent",
            )

        assert "does not exist" in str(exc_info.value)

    @patch("vantage_cli.commands.profile.crud._get_all_profiles")
    @patch("vantage_cli.commands.profile.crud.get_effective_json_output")
    @patch("vantage_cli.commands.profile.crud.print_json")
    def test_delete_default_profile_without_force_json(
        self,
        mock_print_json,
        mock_json_output,
        mock_get_profiles,
        mock_context,
    ):
        """Test deleting default profile without force flag with JSON output."""
        # Setup mocks
        mock_get_profiles.return_value = {"default": {}}
        mock_json_output.return_value = True

        # Call the function
        delete_profile(
            ctx=mock_context,
            profile_name="default",
        )

        # Verify JSON error response
        mock_print_json.assert_called_once()
        result = mock_print_json.call_args[1]["data"]
        assert result["success"] is False
        assert result["profile_name"] == "default"
        assert "Cannot delete 'default'" in result["message"]

    @patch("vantage_cli.commands.profile.crud._get_all_profiles")
    @patch("vantage_cli.commands.profile.crud.get_effective_json_output")
    def test_delete_default_profile_without_force_raises_abort(
        self,
        mock_json_output,
        mock_get_profiles,
        mock_context,
    ):
        """Test deleting default profile without force raises Abort."""
        # Setup mocks
        mock_get_profiles.return_value = {"default": {}}
        mock_json_output.return_value = False

        # Call should raise Abort
        with pytest.raises(Abort) as exc_info:
            delete_profile(
                ctx=mock_context,
                profile_name="default",
            )

        assert "Cannot delete 'default'" in str(exc_info.value)

    @patch("vantage_cli.commands.profile.crud._get_all_profiles")
    @patch("vantage_cli.commands.profile.crud.get_effective_json_output")
    @patch("vantage_cli.commands.profile.crud._clear_profile_token_cache")
    @patch("vantage_cli.commands.profile.crud.USER_CONFIG_FILE")
    @patch("vantage_cli.commands.profile.crud.USER_TOKEN_CACHE_DIR")
    @patch("vantage_cli.commands.profile.crud.print_json")
    @patch("shutil.rmtree")
    def test_delete_profile_success_json(
        self,
        mock_rmtree,
        mock_print_json,
        mock_cache_dir,
        mock_config_file,
        mock_clear_cache,
        mock_json_output,
        mock_get_profiles,
        mock_context,
    ):
        """Test successful profile deletion with JSON output."""
        # Setup mocks
        mock_get_profiles.return_value = {"test-profile": {}}
        mock_json_output.return_value = True
        mock_config_file.exists.return_value = True
        mock_config_file.read_text.return_value = '{"test-profile": {}, "other": {}}'

        # Mock cache directory
        profile_cache_dir = Mock()
        profile_cache_dir.exists.return_value = True
        mock_cache_dir.__truediv__.return_value = profile_cache_dir

        # Call the function
        delete_profile(
            ctx=mock_context,
            profile_name="test-profile",
            force=True,
        )

        # Verify success response
        mock_print_json.assert_called_once()
        result = mock_print_json.call_args[1]["data"]
        assert result["success"] is True
        assert result["profile_name"] == "test-profile"
        assert "deleted successfully" in result["message"]

        # Verify cleanup calls
        mock_clear_cache.assert_called_once_with("test-profile")
        mock_config_file.write_text.assert_called_once()


class TestGetProfile:
    """Test profile retrieval functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock typer context."""
        ctx = Mock(spec=typer.Context)
        ctx.obj = SimpleNamespace(profile=None, verbose=False, json_output=False)
        ctx.params = {"json_output": False}
        return ctx

    @pytest.fixture
    def sample_profile_data(self):
        """Sample profile data."""
        return {
            "api_base_url": "https://apis.vantagecompute.ai",
            "oidc_base_url": "https://auth.vantagecompute.ai",
            "oidc_client_id": "default",
            "oidc_max_poll_time": 300,
        }

    @patch("vantage_cli.commands.profile.crud._get_all_profiles")
    @patch("vantage_cli.commands.profile.crud.get_effective_json_output")
    @patch("vantage_cli.commands.profile.crud.print_json")
    def test_get_nonexistent_profile_json(
        self,
        mock_print_json,
        mock_json_output,
        mock_get_profiles,
        mock_context,
    ):
        """Test getting non-existent profile with JSON output."""
        # Setup mocks
        mock_get_profiles.return_value = {}
        mock_json_output.return_value = True

        # Call the function
        get_profile(
            ctx=mock_context,
            profile_name="nonexistent",
        )

        # Verify JSON error response
        mock_print_json.assert_called_once()
        result = mock_print_json.call_args[1]["data"]
        assert result["success"] is False
        assert result["profile_name"] == "nonexistent"
        assert "does not exist" in result["message"]

    @patch("vantage_cli.commands.profile.crud._get_all_profiles")
    @patch("vantage_cli.commands.profile.crud.get_effective_json_output")
    def test_get_nonexistent_profile_raises_abort(
        self,
        mock_json_output,
        mock_get_profiles,
        mock_context,
    ):
        """Test getting non-existent profile raises Abort."""
        # Setup mocks
        mock_get_profiles.return_value = {}
        mock_json_output.return_value = False

        # Call should raise Abort
        with pytest.raises(Abort) as exc_info:
            get_profile(
                ctx=mock_context,
                profile_name="nonexistent",
            )

        assert "does not exist" in str(exc_info.value)

    @patch("vantage_cli.commands.profile.crud._get_all_profiles")
    @patch("vantage_cli.commands.profile.crud.get_effective_json_output")
    @patch("vantage_cli.commands.profile.crud.print_json")
    def test_get_profile_success_json(
        self,
        mock_print_json,
        mock_json_output,
        mock_get_profiles,
        mock_context,
        sample_profile_data,
    ):
        """Test successful profile retrieval with JSON output."""
        # Setup mocks
        mock_get_profiles.return_value = {"test-profile": sample_profile_data}
        mock_json_output.return_value = True

        # Call the function
        get_profile(
            ctx=mock_context,
            profile_name="test-profile",
        )

        # Verify success response
        mock_print_json.assert_called_once()
        result = mock_print_json.call_args[1]["data"]
        assert result["success"] is True
        assert result["profile_name"] == "test-profile"
        assert "settings" in result
        assert result["settings"]["api_base_url"] == sample_profile_data["api_base_url"]

    @patch("vantage_cli.commands.profile.crud._get_all_profiles")
    @patch("vantage_cli.commands.profile.crud.get_effective_json_output")
    @patch("vantage_cli.commands.profile.crud._render_profile_details")
    def test_get_profile_success_rich(
        self,
        mock_render_details,
        mock_json_output,
        mock_get_profiles,
        mock_context,
        sample_profile_data,
    ):
        """Test successful profile retrieval with Rich output."""
        # Setup mocks
        mock_get_profiles.return_value = {"test-profile": sample_profile_data}
        mock_json_output.return_value = False

        # Call the function
        get_profile(
            ctx=mock_context,
            profile_name="test-profile",
        )

        # Verify render was called
        mock_render_details.assert_called_once()
        args = mock_render_details.call_args[0]
        assert args[0] == "test-profile"
        assert isinstance(args[1], Settings)


class TestListProfiles:
    """Test profile listing functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock typer context."""
        ctx = Mock(spec=typer.Context)
        ctx.obj = SimpleNamespace(profile=None, verbose=False, json_output=False)
        ctx.params = {"json_output": False}
        return ctx

    @pytest.fixture
    def sample_profiles(self):
        """Sample profiles data."""
        return {
            "default": {
                "api_base_url": "https://apis.vantagecompute.ai",
                "oidc_base_url": "https://auth.vantagecompute.ai",
                "oidc_client_id": "default",
                "oidc_max_poll_time": 300,
            },
            "staging": {
                "api_base_url": "https://staging-apis.vantagecompute.ai",
                "oidc_base_url": "https://staging-auth.vantagecompute.ai",
                "oidc_client_id": "staging",
                "oidc_max_poll_time": 300,
            },
        }

    @patch("vantage_cli.commands.profile.crud.get_active_profile")
    @patch("vantage_cli.commands.profile.crud._get_all_profiles")
    @patch("vantage_cli.commands.profile.crud.get_effective_json_output")
    @patch("vantage_cli.commands.profile.crud.print_json")
    def test_list_profiles_empty_json(
        self,
        mock_print_json,
        mock_json_output,
        mock_get_profiles,
        mock_active_profile,
        mock_context,
    ):
        """Test listing profiles when none exist with JSON output."""
        # Setup mocks
        mock_get_profiles.return_value = {}
        mock_active_profile.return_value = "default"
        mock_json_output.return_value = True

        # Call the function
        list_profiles(ctx=mock_context)

        # Verify JSON response
        mock_print_json.assert_called_once()
        result = mock_print_json.call_args[1]["data"]
        assert result["profiles"] == []
        assert result["total"] == 0
        assert result["current_profile"] == "default"

    @patch("vantage_cli.commands.profile.crud.get_active_profile")
    @patch("vantage_cli.commands.profile.crud._get_all_profiles")
    @patch("vantage_cli.commands.profile.crud.get_effective_json_output")
    @patch("vantage_cli.commands.profile.crud.print_json")
    def test_list_profiles_success_json(
        self,
        mock_print_json,
        mock_json_output,
        mock_get_profiles,
        mock_active_profile,
        mock_context,
        sample_profiles,
    ):
        """Test successful profile listing with JSON output."""
        # Setup mocks
        mock_get_profiles.return_value = sample_profiles
        mock_active_profile.return_value = "default"
        mock_json_output.return_value = True

        # Call the function
        list_profiles(ctx=mock_context)

        # Verify JSON response
        mock_print_json.assert_called_once()
        result = mock_print_json.call_args[1]["data"]
        assert result["total"] == 2
        assert result["current_profile"] == "default"
        assert len(result["profiles"]) == 2

        # Check profile data structure
        profile_names = {p["name"] for p in result["profiles"]}
        assert profile_names == {"default", "staging"}

        # Check current profile marking
        default_profile = next(p for p in result["profiles"] if p["name"] == "default")
        assert default_profile["is_current"] is True

    @patch("vantage_cli.commands.profile.crud.get_active_profile")
    @patch("vantage_cli.commands.profile.crud._get_all_profiles")
    @patch("vantage_cli.commands.profile.crud.get_effective_json_output")
    @patch("vantage_cli.commands.profile.crud._render_profiles_table")
    def test_list_profiles_success_rich(
        self,
        mock_render_table,
        mock_json_output,
        mock_get_profiles,
        mock_active_profile,
        mock_context,
        sample_profiles,
    ):
        """Test successful profile listing with Rich output."""
        # Setup mocks
        mock_get_profiles.return_value = sample_profiles
        mock_active_profile.return_value = "default"
        mock_json_output.return_value = False

        # Call the function
        list_profiles(ctx=mock_context)

        # Verify render was called
        mock_render_table.assert_called_once()
        args = mock_render_table.call_args[0]
        assert args[0] == sample_profiles
        assert args[1] == "default"


class TestUseProfile:
    """Test profile activation functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock typer context."""
        ctx = Mock(spec=typer.Context)
        ctx.obj = SimpleNamespace(profile=None, verbose=False, json_output=False)
        ctx.params = {"json_output": False}
        return ctx

    @pytest.fixture
    def sample_profiles(self):
        """Sample profiles data."""
        return {
            "default": {},
            "staging": {},
        }

    @patch("vantage_cli.commands.profile.crud._get_all_profiles")
    @patch("vantage_cli.commands.profile.crud.get_effective_json_output")
    @patch("vantage_cli.commands.profile.crud.print_json")
    def test_use_nonexistent_profile_json(
        self,
        mock_print_json,
        mock_json_output,
        mock_get_profiles,
        mock_context,
        sample_profiles,
    ):
        """Test using non-existent profile with JSON output."""
        # Setup mocks
        mock_get_profiles.return_value = sample_profiles
        mock_json_output.return_value = True

        # Call the function
        use_profile(
            ctx=mock_context,
            profile_name="nonexistent",
        )

        # Verify JSON error response
        mock_print_json.assert_called_once()
        result = mock_print_json.call_args[1]["data"]
        assert result["success"] is False
        assert result["profile_name"] == "nonexistent"
        assert "does not exist" in result["message"]
        assert "available_profiles" in result
        assert set(result["available_profiles"]) == {"default", "staging"}

    @patch("vantage_cli.commands.profile.crud._get_all_profiles")
    @patch("vantage_cli.commands.profile.crud.get_effective_json_output")
    def test_use_nonexistent_profile_raises_exit(
        self,
        mock_json_output,
        mock_get_profiles,
        mock_context,
        sample_profiles,
    ):
        """Test using non-existent profile raises typer.Exit."""
        # Setup mocks
        mock_get_profiles.return_value = sample_profiles
        mock_json_output.return_value = False

        # Call should raise typer.Exit
        with pytest.raises(typer.Exit) as exc_info:
            use_profile(
                ctx=mock_context,
                profile_name="nonexistent",
            )

        assert exc_info.value.exit_code == 1

    @patch("vantage_cli.commands.profile.crud._get_all_profiles")
    @patch("vantage_cli.commands.profile.crud.get_effective_json_output")
    @patch("vantage_cli.commands.profile.crud.set_active_profile")
    @patch("vantage_cli.commands.profile.crud.print_json")
    def test_use_profile_success_json(
        self,
        mock_print_json,
        mock_set_active,
        mock_json_output,
        mock_get_profiles,
        mock_context,
        sample_profiles,
    ):
        """Test successful profile activation with JSON output."""
        # Setup mocks
        mock_get_profiles.return_value = sample_profiles
        mock_json_output.return_value = True

        # Call the function
        use_profile(
            ctx=mock_context,
            profile_name="staging",
        )

        # Verify activation
        mock_set_active.assert_called_once_with("staging")

        # Verify success response
        mock_print_json.assert_called_once()
        result = mock_print_json.call_args[1]["data"]
        assert result["success"] is True
        assert result["profile_name"] == "staging"
        assert "is now active" in result["message"]

    @patch("vantage_cli.commands.profile.crud._get_all_profiles")
    @patch("vantage_cli.commands.profile.crud.get_effective_json_output")
    @patch("vantage_cli.commands.profile.crud.set_active_profile")
    @patch("vantage_cli.commands.profile.crud.Console")
    def test_use_profile_success_rich(
        self,
        mock_console_class,
        mock_set_active,
        mock_json_output,
        mock_get_profiles,
        mock_context,
        sample_profiles,
    ):
        """Test successful profile activation with Rich output."""
        # Setup mocks
        mock_get_profiles.return_value = sample_profiles
        mock_json_output.return_value = False
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        # Call the function
        use_profile(
            ctx=mock_context,
            profile_name="staging",
        )

        # Verify activation
        mock_set_active.assert_called_once_with("staging")

        # Verify console output
        mock_console.print.assert_called()


class TestHelperFunctions:
    """Test helper functions."""

    @patch("vantage_cli.commands.profile.crud.USER_CONFIG_FILE")
    def test_get_all_profiles_file_not_exists(self, mock_config_file):
        """Test _get_all_profiles when config file doesn't exist."""
        from vantage_cli.commands.profile.crud import _get_all_profiles

        mock_config_file.exists.return_value = False

        result = _get_all_profiles()

        assert result == {}

    @patch("vantage_cli.commands.profile.crud.USER_CONFIG_FILE")
    def test_get_all_profiles_success(self, mock_config_file):
        """Test _get_all_profiles with valid config file."""
        from vantage_cli.commands.profile.crud import _get_all_profiles

        sample_data = {"default": {}, "staging": {}}
        mock_config_file.exists.return_value = True
        mock_config_file.read_text.return_value = json.dumps(sample_data)

        result = _get_all_profiles()

        assert result == sample_data

    @patch("vantage_cli.commands.profile.crud.USER_CONFIG_FILE")
    def test_get_all_profiles_json_decode_error(self, mock_config_file):
        """Test _get_all_profiles with invalid JSON."""
        from vantage_cli.commands.profile.crud import _get_all_profiles

        mock_config_file.exists.return_value = True
        mock_config_file.read_text.return_value = "invalid json"

        result = _get_all_profiles()

        assert result == {}

    @patch("vantage_cli.commands.profile.crud.Console")
    def test_render_profiles_table(self, mock_console_class):
        """Test _render_profiles_table function."""
        from vantage_cli.commands.profile.crud import _render_profiles_table

        mock_console = Mock()
        mock_console_class.return_value = mock_console

        profiles = {
            "default": {
                "api_base_url": "https://apis.vantagecompute.ai",
                "oidc_base_url": "https://auth.vantagecompute.ai",
                "oidc_client_id": "default",
            },
            "staging": {
                "api_base_url": "https://staging-apis.vantagecompute.ai",
                "oidc_base_url": "https://staging-auth.vantagecompute.ai",
                "oidc_client_id": "staging",
            },
        }

        _render_profiles_table(profiles, "default")

        # Verify console was used
        mock_console.print.assert_called()

    @patch("vantage_cli.commands.profile.crud.Console")
    def test_render_profile_details(self, mock_console_class):
        """Test _render_profile_details function."""
        from vantage_cli.commands.profile.crud import _render_profile_details

        mock_console = Mock()
        mock_console_class.return_value = mock_console

        settings = Settings(
            api_base_url="https://apis.vantagecompute.ai",
            oidc_base_url="https://auth.vantagecompute.ai",
            oidc_client_id="default",
            oidc_max_poll_time=300,
        )

        _render_profile_details("test-profile", settings)

        # Verify console was used
        mock_console.print.assert_called()


class TestProfileCommandIntegration:
    """Integration tests for profile command typer app."""

    def test_profile_app_commands_registered(self):
        """Test that all profile commands are properly registered."""
        try:
            from vantage_cli.commands.profile import profile_app
        except ImportError:
            pytest.skip("Profile app not available")
            return

        # Get registered commands - it's a list, not dict
        commands = profile_app.registered_commands
        command_names = {cmd.name for cmd in commands}

        # Verify all expected commands are registered
        expected_commands = {"create", "delete", "get", "list", "use"}
        assert command_names == expected_commands

    def test_profile_app_configuration(self):
        """Test profile app configuration."""
        try:
            from vantage_cli.commands.profile import profile_app
        except ImportError:
            pytest.skip("Profile app not available")
            return

        # Verify app configuration
        assert profile_app.info.name == "profile"
        assert "Manage Vantage CLI profiles" in profile_app.info.help
        assert profile_app.info.invoke_without_command is True
        assert profile_app.info.no_args_is_help is True
