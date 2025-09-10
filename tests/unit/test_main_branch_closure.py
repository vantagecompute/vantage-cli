"""Additional tests to close remaining uncovered branches in `vantage_cli.main`."""

import json
import runpy
import sys
import warnings
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
import typer

from vantage_cli.main import whoami
from vantage_cli.schemas import IdentityData, Persona, TokenSet


@pytest.mark.asyncio
async def test_whoami_minimal_rich_table_no_optional_fields():
    """Covers False branches for optional token metadata rows (name, user_id, issued, expires)."""
    with (
        patch("vantage_cli.main.extract_persona") as mock_extract,
        patch("vantage_cli.main.jwt.decode") as mock_decode,
        patch("vantage_cli.main.print_json") as mock_print_json,
        patch("vantage_cli.config.USER_CONFIG_FILE") as mock_config_file,
    ):
        ctx = Mock(spec=typer.Context)
        ctx.obj = SimpleNamespace(profile="minimal", json_output=False)

        # Provide empty settings mapping for profile
        mock_config_file.read_text.return_value = json.dumps({"minimal": {}})

        # Persona with access token; jwt.decode returns empty dict so no optional keys
        identity = IdentityData(email="min@example.com", client_id="cid-min")
        persona = Persona(token_set=TokenSet(access_token="tok"), identity_data=identity)
        mock_extract.return_value = persona
        mock_decode.return_value = {}

        await whoami(ctx)

        mock_print_json.assert_not_called()
        mock_extract.assert_called_once_with("minimal")
        mock_decode.assert_called_once()


def test_main_module_entrypoint_calls_app(capsys):
    """Execute module as __main__ to cover guard line using a harmless help invocation.

    We pass a valid subcommand (profile --help) so Click exits with code 0 and
    we avoid the error code 2 path triggered by missing command parsing.
    """
    original_argv = sys.argv[:]
    sys.argv = ["vantage", "profile", "--help"]
    try:
        # Suppress the benign RuntimeWarning about the module already being in sys.modules
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="'vantage_cli.main' found in sys.modules",
                category=RuntimeWarning,
            )
            with pytest.raises(SystemExit) as exc:
                runpy.run_module("vantage_cli.main", run_name="__main__")
        assert exc.value.code == 0
        captured = capsys.readouterr()
        assert "profile" in captured.out
    finally:
        sys.argv = original_argv
