from pathlib import Path
from types import SimpleNamespace

import pytest
import typer

from vantage_cli import render as core_render
from vantage_cli.commands.cloud import render as clouds_render
from vantage_cli.commands.cloud.add import add_command
from vantage_cli.commands.cloud.delete import delete_command
from vantage_cli.commands.cloud.update import update_command


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
    clouds_render.render_clouds_table([])
    out = capsys.readouterr().out
    assert "No cloud accounts found" in out


def test_render_clouds_table_json(capsys):
    data = [{"name": "c1", "provider": "aws", "status": "READY", "accountId": "acc1"}]
    clouds_render.render_clouds_table(data, json_output=True)
    out = capsys.readouterr().out
    assert '"clouds"' in out and '"c1"' in out


def test_render_clouds_table_table(capsys):
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
    clouds_render.render_clouds_table(data)
    out = capsys.readouterr().out
    assert "Cloud Accounts" in out
    assert "c1" in out and "c2" in out


def test_render_cloud_operation_result_json(capsys):
    clouds_render.render_cloud_operation_result(
        "add", "c1", success=True, details={"region": "us-east-1"}, json_output=True
    )
    out = capsys.readouterr().out
    assert '"operation"' in out and '"add"' in out


def test_render_cloud_operation_result_panel(capsys):
    clouds_render.render_cloud_operation_result(
        "delete", "c2", success=False, details={"error": "not found"}
    )
    out = capsys.readouterr().out
    assert "Cloud account" in out and "not found" in out


def test_render_quick_start_guide(capsys):
    core_render.render_quick_start_guide()
    out = capsys.readouterr().out
    assert "Quick Start Guide" in out
