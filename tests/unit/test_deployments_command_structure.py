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
"""Tests for the deployment command structure."""

import inspect
from unittest.mock import Mock, patch

import typer

from vantage_cli.commands.deployment import deployment_app


class TestDeploymentCommandStructure:
    """Tests for the deployment command structure and registration."""

    def test_deployment_app_is_typer_instance(self):
        """Test that deployment_app is a typer.Typer instance."""
        assert isinstance(deployment_app, typer.Typer)

    def test_deployment_commands_registered(self):
        """Test that the expected commands are registered."""
        # Get the registered commands - it's a list, not dict
        commands = deployment_app.registered_commands
        command_names = {cmd.name for cmd in commands}

        # Verify that main deployment commands are registered
        assert "list" in command_names
        assert "create" in command_names
        assert "delete" in command_names

        # Verify we no longer have the app subgroup (apps moved to top-level)
        groups = deployment_app.registered_groups
        app_group_names = {group.typer_instance.info.name for group in groups}
        assert "app" not in app_group_names

        # Verify we don't have the old individual app commands
        assert "slurm-juju-localhost" not in command_names
        assert "slurm-multipass-localhost" not in command_names

    def test_app_subgroup_no_longer_exists(self):
        """Test that the app subgroup no longer exists (moved to top-level)."""
        # Find the app subgroup in registered_groups - should not exist
        groups = deployment_app.registered_groups
        app_subgroup = next((group for group in groups if group.name == "app"), None)
        assert app_subgroup is None

    @patch("vantage_cli.commands.deployment.list.list_deployments")
    def test_list_command_function(self, mock_list_deployments: Mock) -> None:
        """Test that the list command is properly connected."""
        # Find the list command
        commands = deployment_app.registered_commands
        list_command = next((cmd for cmd in commands if cmd.name == "list"), None)

        # Verify the command exists
        assert list_command is not None

    @patch("vantage_cli.commands.deployment.create.create_deployment")
    def test_create_command_function(self, mock_create_deployment: Mock) -> None:
        """Test that the create command is properly connected."""
        # Find the create command
        commands = deployment_app.registered_commands
        create_command = next((cmd for cmd in commands if cmd.name == "create"), None)

        # Verify the command exists
        assert create_command is not None

    @patch("vantage_cli.commands.deployment.delete.delete_deployment")
    def test_delete_command_function(self, mock_delete_deployment: Mock) -> None:
        """Test that the delete command is properly connected."""
        # Find the delete command
        commands = deployment_app.registered_commands
        delete_command = next((cmd for cmd in commands if cmd.name == "delete"), None)

        # Verify the command exists
        assert delete_command is not None

    def test_create_command_parameters(self):
        """Test that the create command has the correct parameters."""
        # Find the create command
        commands = deployment_app.registered_commands
        create_command = next((cmd for cmd in commands if cmd.name == "create"), None)

        assert create_command is not None

        # Get the parameter names from the command's callback signature
        callback = create_command.callback
        if callback is not None:
            sig = inspect.signature(callback)
            param_names = list(sig.parameters.keys())

            # Verify expected parameters are present
            assert "ctx" in param_names
            assert "app_name" in param_names
            assert "cluster_name" in param_names
            assert "dev_run" in param_names
            assert "name" in param_names

    def test_delete_command_parameters(self):
        """Test that the delete command has the correct parameters."""
        # Find the delete command
        commands = deployment_app.registered_commands
        delete_command = next((cmd for cmd in commands if cmd.name == "delete"), None)

        assert delete_command is not None

        # Get the parameter names from the command's callback signature
        callback = delete_command.callback
        if callback is not None:
            sig = inspect.signature(callback)
            param_names = list(sig.parameters.keys())

            # Verify expected parameters are present
            assert "ctx" in param_names
            assert "deployment_id" in param_names
            assert "force" in param_names
