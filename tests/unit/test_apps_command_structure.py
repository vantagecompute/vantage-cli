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
"""Tests for the apps command structure."""

from unittest.mock import patch

import typer

from vantage_cli.apps import apps_app


class TestAppsCommandStructure:
    """Tests for the apps command structure and registration."""

    def test_apps_app_is_typer_instance(self):
        """Test that apps_app is a typer.Typer instance."""
        assert isinstance(apps_app, typer.Typer)

    def test_apps_commands_registered(self):
        """Test that the expected commands are registered."""
        # Get the registered commands - it's a list, not dict
        commands = apps_app.registered_commands
        command_names = {cmd.name for cmd in commands}

        # Verify that list and deploy commands are registered
        assert "list" in command_names
        assert "deploy" in command_names

        # Verify we don't have the old individual app commands
        assert "slurm-juju-localhost" not in command_names
        assert "slurm-multipass-localhost" not in command_names

    @patch("vantage_cli.commands.app.list.list_apps")
    def test_list_command_function(self, mock_list_apps):
        """Test that the list command is properly connected."""
        # Find the list command
        commands = apps_app.registered_commands
        list_command = next((cmd for cmd in commands if cmd.name == "list"), None)

        # Verify the command function is the expected one
        assert list_command is not None
        assert list_command.callback.__name__ == "list_apps"

    @patch("vantage_cli.commands.app.deploy.deploy_app")
    def test_deploy_command_function(self, mock_deploy_app):
        """Test that the deploy command is properly connected."""
        # Find the deploy command
        commands = apps_app.registered_commands
        deploy_command = next((cmd for cmd in commands if cmd.name == "deploy"), None)

        # Verify the command function is the expected one
        assert deploy_command is not None
        assert deploy_command.callback.__name__ == "deploy_app"

    def test_deploy_command_parameters(self):
        """Test that the deploy command has the correct parameters."""
        # Find the deploy command
        commands = apps_app.registered_commands
        deploy_command = next((cmd for cmd in commands if cmd.name == "deploy"), None)

        assert deploy_command is not None

        # Get the parameter names from the command's callback signature
        callback = deploy_command.callback
        import inspect

        sig = inspect.signature(callback)
        param_names = list(sig.parameters.keys())

        # Verify that we have the expected parameters
        assert "ctx" in param_names
        assert "app_name" in param_names
        assert "cluster_name" in param_names

        # Verify parameter annotations (they should be Annotated with typer.Argument)
        app_name_param = sig.parameters["app_name"]
        cluster_name_param = sig.parameters["cluster_name"]

        # Check that both are annotated with typer.Argument
        assert hasattr(app_name_param.annotation, "__origin__")  # Annotated type
        assert hasattr(cluster_name_param.annotation, "__origin__")  # Annotated type
