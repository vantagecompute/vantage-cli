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
import re

from vantage_cli.commands.profile import render as profile_render


def _strip_ansi(text: str) -> str:
    # Helper to make substring assertions easier
    ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
    return ansi_escape.sub("", text)


def test_render_profile_operation_result_success_with_details(capsys):
    details = {
        "client_id": "abc123",
        "client_secret": None,  # Should be skipped
        "description": "Test profile",
        "owner_email": "user@example.com",
    }
    profile_render.render_profile_operation_result(
        operation="create", profile_name="test-profile", success=True, details=details
    )

    out = _strip_ansi(capsys.readouterr().out)
    assert "Profile 'test-profile' create successful" in out
    # Table headers converted to Title Case with spaces
    assert "Client Id" in out
    assert "Description" in out
    assert "Owner Email" in out
    # Skipped None value
    assert "Client Secret" not in out


def test_render_profile_operation_result_failure_no_details(capsys):
    profile_render.render_profile_operation_result(
        operation="delete", profile_name="prod", success=False, details=None
    )
    out = _strip_ansi(capsys.readouterr().out)
    assert "Profile 'prod' delete failed" in out
    # No details table should be rendered
    assert "Profile Details" not in out
