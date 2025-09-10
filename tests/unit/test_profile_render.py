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
