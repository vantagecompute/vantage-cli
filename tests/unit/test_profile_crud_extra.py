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
#!/usr/bin/env python3
"""Extra coverage tests for ``vantage_cli.commands.profile.crud``.

Exercise JSON vs rich output paths, activation/overwrite flows, early returns,
and exception handling.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import click
import pytest

from vantage_cli.commands.profile.crud import (
    create_profile,
    delete_profile,
    get_profile,
    list_profiles,
    use_profile,
)

# ---------------------------------------------------------------------------
# create_profile extra branches
# ---------------------------------------------------------------------------


def test_create_profile_existing_json():
    """Existing profile with JSON output should early-return (no Abort)."""
    mock_ctx = MagicMock()
    mock_ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=True)
    existing = {"p": {"api_base_url": "u"}}
    with patch("vantage_cli.commands.profile.crud._get_all_profiles", return_value=existing):
        with patch(
            "vantage_cli.commands.profile.crud.get_effective_json_output", return_value=True
        ):
            with patch("vantage_cli.commands.profile.crud.print_json") as pj:
                create_profile(mock_ctx, "p")
                assert pj.called


def test_create_profile_activate_json():
    """Activation + JSON path should include set active message."""
    mock_ctx = MagicMock()
    mock_ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=True)
    with patch("vantage_cli.commands.profile.crud._get_all_profiles", return_value={}):
        with patch("vantage_cli.commands.profile.crud.init_user_filesystem"):
            with patch("vantage_cli.commands.profile.crud.dump_settings"):
                with patch("vantage_cli.commands.profile.crud.set_active_profile") as sap:
                    with patch(
                        "vantage_cli.commands.profile.crud.get_effective_json_output",
                        return_value=True,
                    ):
                        with patch("vantage_cli.commands.profile.crud.print_json") as pj:
                            create_profile(mock_ctx, "newp", activate=True)
                            sap.assert_called_once_with("newp")
                            data = pj.call_args[1]["data"]
                            assert data["is_active"] is True
                            assert "set as active" in data["message"].lower()


def test_create_profile_activate_rich():
    """Activation + rich path; ensure set_active_profile called and details rendered."""
    mock_ctx = MagicMock()
    mock_ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=True)
    with patch("vantage_cli.commands.profile.crud._get_all_profiles", return_value={}):
        with patch("vantage_cli.commands.profile.crud.init_user_filesystem"):
            with patch("vantage_cli.commands.profile.crud.dump_settings"):
                with patch("vantage_cli.commands.profile.crud.set_active_profile") as sap:
                    with patch(
                        "vantage_cli.commands.profile.crud.get_effective_json_output",
                        return_value=False,
                    ):
                        # Patch profile details renderer to avoid heavy rich output
                        with patch(
                            "vantage_cli.commands.profile.crud._render_profile_details"
                        ) as rpd:
                            create_profile(mock_ctx, "rp", activate=True)
                            sap.assert_called_once_with("rp")
                            rpd.assert_called_once()


def test_create_profile_exception_json():
    """Exception path (dump_settings fails) with JSON output returns error result."""
    mock_ctx = MagicMock()
    mock_ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=True)
    with patch("vantage_cli.commands.profile.crud._get_all_profiles", return_value={}):
        with patch("vantage_cli.commands.profile.crud.init_user_filesystem"):
            with patch(
                "vantage_cli.commands.profile.crud.dump_settings", side_effect=RuntimeError("boom")
            ):
                with patch(
                    "vantage_cli.commands.profile.crud.get_effective_json_output",
                    return_value=True,
                ):
                    with patch("vantage_cli.commands.profile.crud.print_json") as pj:
                        create_profile(mock_ctx, "errp")
                        data = pj.call_args[1]["data"]
                        assert data["success"] is False
                        assert "boom" in data["message"].lower()


def test_create_profile_exception_rich():
    """Exception path (dump_settings fails) with rich output raises Abort."""
    mock_ctx = MagicMock()
    mock_ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=True)
    with patch("vantage_cli.commands.profile.crud._get_all_profiles", return_value={}):
        with patch("vantage_cli.commands.profile.crud.init_user_filesystem"):
            with patch(
                "vantage_cli.commands.profile.crud.dump_settings",
                side_effect=RuntimeError("kaboom"),
            ):
                with patch(
                    "vantage_cli.commands.profile.crud.get_effective_json_output",
                    return_value=False,
                ):
                    with pytest.raises(click.exceptions.Exit) as exc_info:
                        create_profile(mock_ctx, "errpr")
                    assert exc_info.value.exit_code == 1


# ---------------------------------------------------------------------------
# delete_profile extra branches
# ---------------------------------------------------------------------------


def test_delete_profile_not_found_json():
    mock_ctx = MagicMock()
    mock_ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=True)
    with patch("vantage_cli.commands.profile.crud._get_all_profiles", return_value={}):
        with patch(
            "vantage_cli.commands.profile.crud.get_effective_json_output", return_value=True
        ):
            with patch("vantage_cli.commands.profile.crud.print_json") as pj:
                delete_profile(mock_ctx, "missing")
                data = pj.call_args[1]["data"]
                assert data["success"] is False


def test_delete_default_profile_without_force_json():
    mock_ctx = MagicMock()
    mock_ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=True)
    existing = {"default": {"api_base_url": "x"}}
    with patch("vantage_cli.commands.profile.crud._get_all_profiles", return_value=existing):
        with patch(
            "vantage_cli.commands.profile.crud.get_effective_json_output", return_value=True
        ):
            with patch("vantage_cli.commands.profile.crud.print_json") as pj:
                delete_profile(mock_ctx, "default", force=False)
                data = pj.call_args[1]["data"]
                assert data["success"] is False


def test_delete_profile_confirmation_decline(monkeypatch: pytest.MonkeyPatch):
    mock_ctx = MagicMock()
    mock_ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=True)
    existing = {"p": {"api_base_url": "x"}}
    with patch("vantage_cli.commands.profile.crud._get_all_profiles", return_value=existing):
        with patch(
            "vantage_cli.commands.profile.crud.get_effective_json_output", return_value=False
        ):
            with patch("vantage_cli.commands.profile.crud.USER_CONFIG_FILE") as cfg:
                cfg.exists.return_value = True
                cfg.read_text.return_value = json.dumps(existing)
                with patch("vantage_cli.commands.profile.crud._clear_profile_token_cache") as cptc:
                    # Patch the actual rich.prompt.Confirm.ask used at runtime
                    with patch("rich.prompt.Confirm.ask", return_value=False):
                        delete_profile(mock_ctx, "p", force=False)
                        cptc.assert_not_called()  # early return


def test_delete_profile_exception_json():
    mock_ctx = MagicMock()
    mock_ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=True)
    existing = {"p": {"api_base_url": "x"}}
    with patch("vantage_cli.commands.profile.crud._get_all_profiles", return_value=existing):
        with patch(
            "vantage_cli.commands.profile.crud.get_effective_json_output", return_value=True
        ):
            with patch("vantage_cli.commands.profile.crud.USER_CONFIG_FILE") as cfg:
                cfg.exists.return_value = True
                cfg.read_text.return_value = json.dumps(existing)
                # Force exception in token cache clearing
                with patch(
                    "vantage_cli.commands.profile.crud._clear_profile_token_cache",
                    side_effect=RuntimeError("zap"),
                ):
                    with patch("vantage_cli.commands.profile.crud.print_json") as pj:
                        delete_profile(mock_ctx, "p", force=True)
                        data = pj.call_args[1]["data"]
                        assert data["success"] is False


# ---------------------------------------------------------------------------
# get_profile extra branches
# ---------------------------------------------------------------------------


def test_get_profile_not_found_json():
    mock_ctx = MagicMock()
    mock_ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=True)
    with patch("vantage_cli.commands.profile.crud._get_all_profiles", return_value={}):
        with patch(
            "vantage_cli.commands.profile.crud.get_effective_json_output", return_value=True
        ):
            with patch("vantage_cli.commands.profile.crud.print_json") as pj:
                get_profile(mock_ctx, "missing")
                data = pj.call_args[1]["data"]
                assert data["success"] is False


def test_get_profile_exception_json():
    mock_ctx = MagicMock()
    mock_ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=True)
    existing = {"p": {"api_base_url": "https://a", "oidc_base_url": "https://b"}}
    # Make Settings raise by passing bad data (e.g., remove required field? Instead patch Settings)
    with patch("vantage_cli.commands.profile.crud._get_all_profiles", return_value=existing):
        with patch("vantage_cli.commands.profile.crud.Settings", side_effect=RuntimeError("fail")):
            with patch(
                "vantage_cli.commands.profile.crud.get_effective_json_output", return_value=True
            ):
                with patch("vantage_cli.commands.profile.crud.print_json") as pj:
                    get_profile(mock_ctx, "p")
                    data = pj.call_args[1]["data"]
                    assert data["success"] is False


# ---------------------------------------------------------------------------
# list_profiles extra branches
# ---------------------------------------------------------------------------


def test_list_profiles_empty_rich():
    mock_ctx = MagicMock()
    mock_ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=True)
    with patch("vantage_cli.commands.profile.crud.get_active_profile", return_value="none"):
        with patch("vantage_cli.commands.profile.crud._get_all_profiles", return_value={}):
            with patch(
                "vantage_cli.commands.profile.crud.get_effective_json_output", return_value=False
            ):
                # Patch Console to avoid real output
                with patch("vantage_cli.commands.profile.crud.Console") as cons:
                    list_profiles(mock_ctx)
                    assert cons.called


def test_list_profiles_exception_json():
    mock_ctx = MagicMock()
    mock_ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=True)
    with patch("vantage_cli.commands.profile.crud.get_active_profile", return_value="default"):
        with patch(
            "vantage_cli.commands.profile.crud._get_all_profiles",
            side_effect=RuntimeError("explode"),
        ):
            with patch(
                "vantage_cli.commands.profile.crud.get_effective_json_output", return_value=True
            ):
                with patch("vantage_cli.commands.profile.crud.print_json") as pj:
                    list_profiles(mock_ctx)
                    data = pj.call_args[1]["data"]
                    assert data["success"] is False


# ---------------------------------------------------------------------------
# use_profile extra branches
# ---------------------------------------------------------------------------


def test_use_profile_success_rich():
    mock_ctx = MagicMock()
    mock_ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=True)
    existing = {"p": {"api_base_url": "x"}}
    with patch("vantage_cli.commands.profile.crud._get_all_profiles", return_value=existing):
        with patch(
            "vantage_cli.commands.profile.crud.get_effective_json_output", return_value=False
        ):
            with patch("vantage_cli.commands.profile.crud.set_active_profile") as sap:
                with patch("vantage_cli.commands.profile.crud.Console") as cons:
                    use_profile(mock_ctx, "p")
                    sap.assert_called_once_with("p")
                    assert cons.called


def test_use_profile_not_found_json():
    mock_ctx = MagicMock()
    mock_ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=True)
    existing: Dict[str, Any] = {"a": {}, "b": {}}
    with patch("vantage_cli.commands.profile.crud._get_all_profiles", return_value=existing):
        with patch(
            "vantage_cli.commands.profile.crud.get_effective_json_output", return_value=True
        ):
            with patch("vantage_cli.commands.profile.crud.print_json") as pj:
                use_profile(mock_ctx, "missing")
                data = pj.call_args[1]["data"]
                assert data["success"] is False
                assert set(data["available_profiles"]) == {"a", "b"}


def test_use_profile_exception_json():
    mock_ctx = MagicMock()
    mock_ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=True)
    existing = {"p": {"api_base_url": "x"}}
    with patch("vantage_cli.commands.profile.crud._get_all_profiles", return_value=existing):
        with patch(
            "vantage_cli.commands.profile.crud.get_effective_json_output", return_value=True
        ):
            with patch(
                "vantage_cli.commands.profile.crud.set_active_profile",
                side_effect=RuntimeError("dead"),
            ):
                with patch("vantage_cli.commands.profile.crud.print_json") as pj:
                    use_profile(mock_ctx, "p")
                    data = pj.call_args[1]["data"]
                    assert data["success"] is False
                    assert "dead" in data["message"].lower()


def test_use_profile_exception_rich():
    mock_ctx = MagicMock()
    mock_ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=True)
    existing = {"p": {"api_base_url": "x"}}
    with patch("vantage_cli.commands.profile.crud._get_all_profiles", return_value=existing):
        with patch(
            "vantage_cli.commands.profile.crud.get_effective_json_output", return_value=False
        ):
            with patch(
                "vantage_cli.commands.profile.crud.set_active_profile",
                side_effect=RuntimeError("oops"),
            ):
                with pytest.raises(click.exceptions.Exit) as exc_info:
                    use_profile(mock_ctx, "p")
                assert exc_info.value.exit_code == 1


# ---------------------------------------------------------------------------
# Rendering helpers (direct coverage)
# ---------------------------------------------------------------------------

# Removed direct tests of private rendering helpers to avoid private access warnings.
