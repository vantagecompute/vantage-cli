#!/usr/bin/env python3
"""Unit tests for vantage_cli.commands.profile.crud module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from vantage_cli.commands.profile.crud import (
    _clear_profile_token_cache,
    _get_all_profiles,
    create_profile,
    delete_profile,
    get_profile,
    list_profiles,
    use_profile,
)
from vantage_cli.exceptions import Abort


class TestGetAllProfiles:
    """Test the _get_all_profiles helper function."""

    def test_get_all_profiles_with_existing_file(self):
        """Test getting profiles when config file exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"
            test_data = {
                "default": {"api_base_url": "https://api.example.com"},
                "test": {"api_base_url": "https://test.example.com"},
            }
            config_file.write_text(json.dumps(test_data))

            with patch("vantage_cli.commands.profile.crud.USER_CONFIG_FILE", config_file):
                profiles = _get_all_profiles()
                assert len(profiles) == 2
                assert "default" in profiles
                assert "test" in profiles
                assert profiles["default"]["api_base_url"] == "https://api.example.com"

    def test_get_all_profiles_no_file(self):
        """Test getting profiles when config file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "nonexistent.json"

            with patch("vantage_cli.commands.profile.crud.USER_CONFIG_FILE", config_file):
                profiles = _get_all_profiles()
                assert profiles == {}

    def test_get_all_profiles_invalid_json(self):
        """Test getting profiles when config file has invalid JSON."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"
            config_file.write_text("invalid json content")

            with patch("vantage_cli.commands.profile.crud.USER_CONFIG_FILE", config_file):
                profiles = _get_all_profiles()
                assert profiles == {}


class TestClearProfileTokenCache:
    """Test the _clear_profile_token_cache helper function."""

    def test_clear_profile_token_cache(self):
        """Test clearing token cache for a profile."""
        with tempfile.TemporaryDirectory() as temp_dir:
            token_dir = Path(temp_dir) / "tokens" / "test_profile"
            token_dir.mkdir(parents=True)

            access_token = token_dir / "access.token"
            refresh_token = token_dir / "refresh.token"
            access_token.write_text("access_token_content")
            refresh_token.write_text("refresh_token_content")

            with patch(
                "vantage_cli.commands.profile.crud.USER_TOKEN_CACHE_DIR", Path(temp_dir) / "tokens"
            ):
                _clear_profile_token_cache("test_profile")

                assert not access_token.exists()
                assert not refresh_token.exists()

    def test_clear_profile_token_cache_no_directory(self):
        """Test clearing token cache when directory doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch(
                "vantage_cli.commands.profile.crud.USER_TOKEN_CACHE_DIR", Path(temp_dir) / "tokens"
            ):
                # Should not raise an exception
                _clear_profile_token_cache("nonexistent_profile")


class TestCreateProfile:
    """Test the create_profile command function."""

    def test_create_profile_success(self):
        """Test successful profile creation."""
        mock_ctx = MagicMock()

        with patch("vantage_cli.commands.profile.crud._get_all_profiles", return_value={}):
            with patch("vantage_cli.commands.profile.crud.init_user_filesystem") as mock_init:
                with patch("vantage_cli.commands.profile.crud.dump_settings") as mock_dump:
                    with patch(
                        "vantage_cli.commands.profile.crud.get_effective_json_output",
                        return_value=True,
                    ):
                        with patch("vantage_cli.commands.profile.crud.print_json") as mock_print:
                            create_profile(
                                ctx=mock_ctx, profile_name="test_profile", json_output=True
                            )

                            mock_init.assert_called_once_with("test_profile")
                            mock_dump.assert_called_once()
                            mock_print.assert_called_once()

    def test_create_profile_already_exists(self):
        """Test creating profile that already exists without force."""
        mock_ctx = MagicMock()
        existing_profiles = {"test_profile": {"api_base_url": "https://example.com"}}

        with patch(
            "vantage_cli.commands.profile.crud._get_all_profiles", return_value=existing_profiles
        ):
            with patch(
                "vantage_cli.commands.profile.crud.get_effective_json_output", return_value=False
            ):
                with pytest.raises(Abort) as exc_info:
                    create_profile(
                        ctx=mock_ctx, profile_name="test_profile", force=False, json_output=False
                    )

                assert "already exists" in str(exc_info.value)

    def test_create_profile_with_force(self):
        """Test creating profile that already exists with force=True."""
        mock_ctx = MagicMock()
        existing_profiles = {"test_profile": {"api_base_url": "https://example.com"}}

        with patch(
            "vantage_cli.commands.profile.crud._get_all_profiles", return_value=existing_profiles
        ):
            with patch("vantage_cli.commands.profile.crud.init_user_filesystem"):
                with patch("vantage_cli.commands.profile.crud.dump_settings"):
                    with patch(
                        "vantage_cli.commands.profile.crud.get_effective_json_output",
                        return_value=True,
                    ):
                        with patch("vantage_cli.commands.profile.crud.print_json"):
                            create_profile(
                                ctx=mock_ctx,
                                profile_name="test_profile",
                                force=True,
                                json_output=True,
                            )

                            # Should not raise an exception


class TestDeleteProfile:
    """Test the delete_profile command function."""

    def test_delete_profile_success(self):
        """Test successful profile deletion."""
        mock_ctx = MagicMock()
        existing_profiles = {"test_profile": {"api_base_url": "https://example.com"}}

        with patch(
            "vantage_cli.commands.profile.crud._get_all_profiles", return_value=existing_profiles
        ):
            with patch(
                "vantage_cli.commands.profile.crud.get_effective_json_output", return_value=True
            ):
                with patch("vantage_cli.commands.profile.crud.USER_CONFIG_FILE") as mock_config:
                    mock_config.exists.return_value = True
                    mock_config.read_text.return_value = json.dumps(existing_profiles)
                    with patch("vantage_cli.commands.profile.crud._clear_profile_token_cache"):
                        with patch("vantage_cli.commands.profile.crud.print_json"):
                            delete_profile(
                                ctx=mock_ctx,
                                profile_name="test_profile",
                                force=True,
                                json_output=True,
                            )

    def test_delete_profile_not_found(self):
        """Test deleting profile that doesn't exist."""
        mock_ctx = MagicMock()

        with patch("vantage_cli.commands.profile.crud._get_all_profiles", return_value={}):
            with patch(
                "vantage_cli.commands.profile.crud.get_effective_json_output", return_value=False
            ):
                with pytest.raises(Abort) as exc_info:
                    delete_profile(ctx=mock_ctx, profile_name="nonexistent", json_output=False)

                assert "does not exist" in str(exc_info.value)

    def test_delete_default_profile_without_force(self):
        """Test deleting default profile without force flag."""
        mock_ctx = MagicMock()
        existing_profiles = {"default": {"api_base_url": "https://example.com"}}

        with patch(
            "vantage_cli.commands.profile.crud._get_all_profiles", return_value=existing_profiles
        ):
            with patch(
                "vantage_cli.commands.profile.crud.get_effective_json_output", return_value=False
            ):
                with pytest.raises(Abort) as exc_info:
                    delete_profile(
                        ctx=mock_ctx, profile_name="default", force=False, json_output=False
                    )

                assert "Cannot delete 'default' profile" in str(exc_info.value)


class TestGetProfile:
    """Test the get_profile command function."""

    def test_get_profile_success(self):
        """Test successful profile retrieval."""
        mock_ctx = MagicMock()
        existing_profiles = {
            "test_profile": {
                "api_base_url": "https://example.com",
                "oidc_base_url": "https://auth.example.com",
            }
        }

        with patch(
            "vantage_cli.commands.profile.crud._get_all_profiles", return_value=existing_profiles
        ):
            with patch(
                "vantage_cli.commands.profile.crud.get_effective_json_output", return_value=True
            ):
                with patch("vantage_cli.commands.profile.crud.print_json") as mock_print:
                    get_profile(ctx=mock_ctx, profile_name="test_profile", json_output=True)

                    mock_print.assert_called_once()
                    call_args = mock_print.call_args[1]["data"]
                    assert call_args["success"] is True
                    assert call_args["profile_name"] == "test_profile"

    def test_get_profile_not_found(self):
        """Test getting profile that doesn't exist."""
        mock_ctx = MagicMock()

        with patch("vantage_cli.commands.profile.crud._get_all_profiles", return_value={}):
            with patch(
                "vantage_cli.commands.profile.crud.get_effective_json_output", return_value=False
            ):
                with pytest.raises(Abort) as exc_info:
                    get_profile(ctx=mock_ctx, profile_name="nonexistent", json_output=False)

                assert "does not exist" in str(exc_info.value)


class TestListProfiles:
    """Test the list_profiles command function."""

    def test_list_profiles_success(self):
        """Test successful profile listing."""
        mock_ctx = MagicMock()
        existing_profiles = {
            "default": {"api_base_url": "https://api.example.com"},
            "test": {"api_base_url": "https://test.example.com"},
        }

        with patch("vantage_cli.commands.profile.crud.get_active_profile", return_value="default"):
            with patch(
                "vantage_cli.commands.profile.crud._get_all_profiles",
                return_value=existing_profiles,
            ):
                with patch(
                    "vantage_cli.commands.profile.crud.get_effective_json_output",
                    return_value=True,
                ):
                    with patch("vantage_cli.commands.profile.crud.print_json") as mock_print:
                        list_profiles(ctx=mock_ctx, json_output=True)

                        mock_print.assert_called_once()
                        call_args = mock_print.call_args[1]["data"]
                        assert len(call_args["profiles"]) == 2
                        assert call_args["total"] == 2
                        assert call_args["current_profile"] == "default"

    def test_list_profiles_empty(self):
        """Test listing profiles when none exist."""
        mock_ctx = MagicMock()

        with patch("vantage_cli.commands.profile.crud.get_active_profile", return_value="default"):
            with patch("vantage_cli.commands.profile.crud._get_all_profiles", return_value={}):
                with patch(
                    "vantage_cli.commands.profile.crud.get_effective_json_output",
                    return_value=True,
                ):
                    with patch("vantage_cli.commands.profile.crud.print_json") as mock_print:
                        list_profiles(ctx=mock_ctx, json_output=True)

                        mock_print.assert_called_once()
                        call_args = mock_print.call_args[1]["data"]
                        assert call_args["profiles"] == []
                        assert call_args["total"] == 0


class TestUseProfile:
    """Test the use_profile command function."""

    def test_use_profile_success(self):
        """Test successful profile activation."""
        mock_ctx = MagicMock()
        existing_profiles = {"test_profile": {"api_base_url": "https://example.com"}}

        with patch(
            "vantage_cli.commands.profile.crud._get_all_profiles", return_value=existing_profiles
        ):
            with patch(
                "vantage_cli.commands.profile.crud.get_effective_json_output", return_value=True
            ):
                with patch("vantage_cli.commands.profile.crud.set_active_profile") as mock_set:
                    with patch("vantage_cli.commands.profile.crud.print_json") as mock_print:
                        use_profile(ctx=mock_ctx, profile_name="test_profile", json_output=True)

                        mock_set.assert_called_once_with("test_profile")
                        mock_print.assert_called_once()

    def test_use_profile_not_found(self):
        """Test using profile that doesn't exist."""
        mock_ctx = MagicMock()

        with patch("vantage_cli.commands.profile.crud._get_all_profiles", return_value={}):
            with patch(
                "vantage_cli.commands.profile.crud.get_effective_json_output", return_value=False
            ):
                with pytest.raises(typer.Exit):
                    use_profile(ctx=mock_ctx, profile_name="nonexistent", json_output=False)
