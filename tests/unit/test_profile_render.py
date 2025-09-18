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
    from tests.conftest import MockConsole

    console = MockConsole()
    details = {
        "clientId": "client-123",
        "description": "A test profile",
        "owner_email": "user@example.com",
    }
    profile_render.render_profile_operation_result(
        operation="create",
        profile_name="test-profile",
        console=console,
        success=True,
        details=details,
    )

    # Check that console.print was called multiple times (empty line, panel, table, etc.)
    assert console.print.call_count >= 2
    # Check that some Rich object was printed (Panel or Table)
    call_args = [call[0] for call in console.print.call_args_list if call[0]]
    assert any(
        hasattr(arg[0], "renderable") or hasattr(arg[0], "title") for arg in call_args if arg
    )


def test_render_profile_operation_result_failure_no_details(capsys):
    from tests.conftest import MockConsole

    console = MockConsole()
    profile_render.render_profile_operation_result(
        operation="delete", profile_name="prod", console=console, success=False, details=None
    )

    # Check that console.print was called (empty line + panel)
    assert console.print.call_count >= 2
    # Check that some Rich object was printed
    call_args = [call[0] for call in console.print.call_args_list if call[0]]
    assert any(
        hasattr(arg[0], "renderable") or hasattr(arg[0], "title") for arg in call_args if arg
    )
