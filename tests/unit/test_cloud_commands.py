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
from pathlib import Path
from types import SimpleNamespace

import pytest
import typer

from vantage_cli import render as core_render
from vantage_cli.commands.cloud import render as clouds_render
from vantage_cli.commands.cloud.add import add_command
from vantage_cli.commands.cloud.delete import delete_command
from vantage_cli.commands.cloud.update import update_command


def _extract_panel_content(console_calls):
    """Extract text content from Panel objects in console calls."""
    content_list = []
    for call in console_calls:
        args = call[0]  # Get positional arguments
        for arg in args:
            if hasattr(arg, "renderable"):
                # This is a Panel with a renderable
                content_list.append(str(arg.renderable))
            elif hasattr(arg, "__str__"):
                content_list.append(str(arg))
    return "\n".join(content_list)


def _extract_json_content(console_calls):
    """Extract JSON content from print_json calls."""
    for call in console_calls:
        # Check if this was a print_json call by looking at kwargs
        if "data" in call.kwargs:
            return call.kwargs["data"]
    return None


class DummyContext(SimpleNamespace):
    """Lightweight stand-in for typer.Context just needing an .obj dict."""

    pass


@pytest.fixture()
def ctx_verbose():
    return DummyContext(obj={"verbose": True, "settings": {"dummy": True}})


@pytest.fixture()
def ctx_quiet():
    return DummyContext(obj={"verbose": False, "settings": None})


def test_add_command_basic(ctx_quiet, capsys):
    add_command(ctx_quiet, "test-cloud", provider="aws", region=None)
    out = capsys.readouterr().out
    assert "Adding cloud 'test-cloud'" in out
    assert "✅ Cloud 'test-cloud' added successfully" in out


def test_add_command_with_options_verbose(ctx_verbose, tmp_path: Path, capsys, caplog):
    config_file = tmp_path / "cloud.yaml"
    credentials_file = tmp_path / "creds.json"
    config_file.write_text("kind: CloudConfig")
    credentials_file.write_text("{}")
    caplog.set_level("DEBUG")

    add_command(
        ctx_verbose,
        "cloud-2",
        provider="gcp",
        region="us-central1",
        config_file=config_file,
        credentials_file=credentials_file,
    )
    out = capsys.readouterr().out
    assert "config file" in out.lower()
    assert "credentials file" in out.lower()
    # debug logs emitted
    assert any("Provider: gcp" in r.message for r in caplog.records)


def test_update_command_no_updates(ctx_quiet, capsys):
    with pytest.raises(typer.Exit) as exc:
        update_command(ctx_quiet, "cloud-x")
    assert exc.value.exit_code == 1
    out = capsys.readouterr().out
    assert "No updates specified" in out


def test_update_command_with_updates(ctx_verbose, tmp_path: Path, capsys):
    config_file = tmp_path / "new.yaml"
    creds_file = tmp_path / "creds.txt"
    config_file.write_text("x:1")
    creds_file.write_text("secret")
    update_command(
        ctx_verbose,
        "cloud-y",
        provider="aws",
        region="us-east-1",
        config_file=config_file,
        credentials_file=creds_file,
        description="Prod cloud",
    )
    out = capsys.readouterr().out
    assert "Updating cloud 'cloud-y'" in out
    assert "provider: aws" in out.lower()
    assert "✅ Cloud 'cloud-y' updated successfully" in out


def test_delete_command_confirmation_cancel(ctx_quiet, monkeypatch, capsys):
    calls = {"count": 0}

    def fake_confirm(msg):
        calls["count"] += 1
        return False  # user cancels

    monkeypatch.setattr(typer, "confirm", fake_confirm)
    with pytest.raises(typer.Abort):
        delete_command(ctx_quiet, "cloud-z")
    out = capsys.readouterr().out
    assert "Operation cancelled." in out
    assert calls["count"] == 1


def test_delete_command_force_and_remove_credentials(ctx_verbose, capsys):
    # Force skips confirmation; remove_credentials triggers extra output
    delete_command(ctx_verbose, "cloud-a", force=True, remove_credentials=True)
    out = capsys.readouterr().out
    assert "Deleting cloud configuration: cloud-a" in out
    assert "Removing stored credentials" in out
    assert "✅ Cloud 'cloud-a' deleted successfully" in out


def test_delete_command_confirmation_accept(monkeypatch, ctx_quiet, capsys):
    monkeypatch.setattr(typer, "confirm", lambda _: True)
    delete_command(ctx_quiet, "cloud-b", force=False, remove_credentials=False)
    out = capsys.readouterr().out
    assert "Deleting cloud configuration: cloud-b" in out
    assert "✅ Cloud 'cloud-b' deleted successfully" in out


# Render helper tests


def test_render_clouds_table_empty(capsys):
    from tests.conftest import MockConsole

    console = MockConsole()
    clouds_render.render_clouds_table([], console)

    # Check that console.print was called with a Panel containing the expected message
    console.print.assert_called()
    calls = console.print.call_args_list

    # Look for Panel objects in the calls and check their content
    found_message = False
    for call in calls:
        args = call[0]  # Get positional arguments
        for arg in args:
            if hasattr(arg, "renderable") and hasattr(arg.renderable, "__str__"):
                # This is a Panel with a renderable (likely Text)
                if "No cloud accounts found" in str(arg.renderable):
                    found_message = True
                    break
            elif hasattr(arg, "__str__") and "No cloud accounts found" in str(arg):
                found_message = True
                break
        if found_message:
            break

    assert found_message, f"Expected 'No cloud accounts found' in Panel, but got calls: {calls}"


def test_render_clouds_table_json(capsys):
    from tests.conftest import MockConsole

    console = MockConsole()
    data = [{"name": "c1", "provider": "aws", "status": "READY", "accountId": "acc1"}]
    clouds_render.render_clouds_table(data, console, json_output=True)

    # Check that console.print_json was called instead of console.print
    console.print_json.assert_called()
    json_data = _extract_json_content(console.print_json.call_args_list)

    # Verify JSON content contains expected data
    assert json_data is not None
    assert "clouds" in json_data
    assert json_data["clouds"] == data


def test_render_clouds_table_table(capsys):
    from tests.conftest import MockConsole

    console = MockConsole()
    data = [
        {
            "name": "c1",
            "provider": "aws",
            "status": "READY",
            "accountId": "acc1",
            "region": "us-east-1",
        },
        {"name": "c2", "provider": "gcp", "status": "PENDING", "accountId": "acc2"},
    ]
    clouds_render.render_clouds_table(data, console)

    # Check that console.print was called (table rendering)
    console.print.assert_called()

    # Verify that a table was printed - look for Table object in call args
    calls = console.print.call_args_list
    table_found = False
    for call in calls:
        args = call[0]
        for arg in args:
            if hasattr(arg, "add_column") and hasattr(arg, "add_row"):
                # This is a Table object
                table_found = True
                break
        if table_found:
            break

    assert table_found, "Expected a Table object to be printed"


def test_render_cloud_operation_result_json(capsys):
    from tests.conftest import MockConsole

    console = MockConsole()
    clouds_render.render_cloud_operation_result(
        "add", "c1", console, success=True, details={"region": "us-east-1"}, json_output=True
    )

    # Check that console.print_json was called instead of console.print
    console.print_json.assert_called()
    json_data = _extract_json_content(console.print_json.call_args_list)

    # Verify JSON content contains expected fields
    assert json_data is not None
    assert json_data["operation"] == "add"
    assert json_data["cloud_name"] == "c1"
    assert json_data["success"] is True


def test_render_cloud_operation_result_panel(capsys):
    from tests.conftest import MockConsole

    console = MockConsole()
    clouds_render.render_cloud_operation_result(
        "delete", "c2", console, success=False, details={"error": "not found"}
    )

    # Check that console.print was called with panel content
    console.print.assert_called()

    # Check that the print calls contain Rich Panel with expected content
    print_calls = console.print.call_args_list
    found_panel_with_content = False

    for call in print_calls:
        args = call[0]
        for arg in args:
            # Check if this is a Rich Panel object
            if hasattr(arg, "renderable") and hasattr(arg, "title"):
                # This is a Rich Panel, check its content
                panel_content = str(arg.renderable)
                if (
                    "Cloud account" in panel_content
                    and "c2" in panel_content
                    and "delete" in panel_content
                ):
                    found_panel_with_content = True
                    break

    assert found_panel_with_content, (
        f"Expected to find panel with 'Cloud account', 'c2', and 'delete' in content. Print calls: {print_calls}"
    )


def test_render_quick_start_guide(capsys):
    core_render.render_quick_start_guide()
    out = capsys.readouterr().out
    assert "Quick Start Guide" in out
