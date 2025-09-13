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
"""Tests for config commands."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
import typer

from vantage_cli.commands.config.clear import clear_config


class DummyContext(SimpleNamespace):
    """Lightweight stand-in for typer.Context just needing an .obj dict."""

    pass


@pytest.fixture()
def ctx_base():
    return DummyContext(
        obj=SimpleNamespace(verbose=False, settings=None, json_output=False, profile="default")
    )


class TestConfigClear:
    """Test config clear command."""

    def test_clear_config_with_force_console_output(self, ctx_base, capsys):
        """Test config clear with force flag and console output."""
        with patch("vantage_cli.commands.config.clear.clear_settings") as mock_clear:
            ctx_base.obj.json_output = False
            clear_config(ctx_base, force=True)

            mock_clear.assert_called_once()

            # Check output
            out = capsys.readouterr().out
            assert "Configuration Cleared" in out
            assert "✅ All configuration files and cached tokens have been cleared" in out
            assert "vantage login" in out

    def test_clear_config_with_force_json_output(self, ctx_base, capsys):
        """Test config clear with force flag and JSON output."""
        with patch("vantage_cli.commands.config.clear.clear_settings") as mock_clear:
            ctx_base.obj.json_output = True
            clear_config(ctx_base, force=True)

            mock_clear.assert_called_once()

            # Check output
            out = capsys.readouterr().out
            assert '"cleared": true' in out
            assert '"message": "All configuration and tokens cleared successfully"' in out

    def test_clear_config_confirmation_cancelled_console(self, ctx_base, capsys):
        """Test config clear with confirmation cancelled, console output."""
        with patch("vantage_cli.commands.config.clear.clear_settings") as mock_clear:
            with patch("typer.confirm", return_value=False):
                ctx_base.obj.json_output = False
                clear_config(ctx_base, force=False)

                mock_clear.assert_not_called()

                # Check output
                out = capsys.readouterr().out
                assert "Operation cancelled" in out

    def test_clear_config_confirmation_cancelled_json(self, ctx_base, capsys):
        """Test config clear with confirmation cancelled, JSON output."""
        with patch("vantage_cli.commands.config.clear.clear_settings") as mock_clear:
            with patch("typer.confirm", return_value=False):
                ctx_base.obj.json_output = True
                clear_config(ctx_base, force=False)

                mock_clear.assert_not_called()

                # Check output
                out = capsys.readouterr().out
                assert '"cleared": false' in out
                assert '"message": "Operation cancelled"' in out

    def test_clear_config_confirmation_accepted_console(self, ctx_base, capsys):
        """Test config clear with confirmation accepted, console output."""
        with patch("vantage_cli.commands.config.clear.clear_settings") as mock_clear:
            with patch("typer.confirm", return_value=True):
                ctx_base.obj.json_output = False
                clear_config(ctx_base, force=False)

                mock_clear.assert_called_once()

                # Check output
                out = capsys.readouterr().out
                assert "Configuration Cleared" in out
                assert "Warning" in out

    def test_clear_config_confirmation_accepted_json(self, ctx_base, capsys):
        """Test config clear with confirmation accepted, JSON output."""
        with patch("vantage_cli.commands.config.clear.clear_settings") as mock_clear:
            with patch("typer.confirm", return_value=True):
                ctx_base.obj.json_output = True
                clear_config(ctx_base, force=False)

                mock_clear.assert_called_once()

                # Check output
                out = capsys.readouterr().out
                assert '"cleared": true' in out
                assert "Warning" in out


class TestConfigCommandStructure:
    """Test config command structure and registration."""

    def test_config_app_is_typer_instance(self):
        """Test that config_app is a Typer instance."""
        from vantage_cli.commands.config import config_app

        assert isinstance(config_app, typer.Typer)
        assert config_app.info.name == "config"
        assert "Manage Vantage CLI configuration" in config_app.info.help

    def test_config_commands_registered(self):
        """Test that config commands are properly registered."""
        from vantage_cli.commands.config import config_app

        # Get command names
        command_names = [cmd.name for cmd in config_app.registered_commands]
        assert "clear" in command_names

    def test_clear_command_function(self):
        """Test that clear command points to the correct function."""
        from vantage_cli.commands.config import config_app
        from vantage_cli.commands.config.clear import clear_config

        clear_command = next(cmd for cmd in config_app.registered_commands if cmd.name == "clear")
        assert clear_command.callback.__name__ == clear_config.__name__
        assert clear_command.callback.__module__ == clear_config.__module__
