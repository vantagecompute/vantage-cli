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
"""Tests for license commands."""


class TestLicenseCommandStructure:
    """Test license command structure and configuration."""

    def test_license_app_is_typer_instance(self):
        """Test that license_app is properly configured."""
        from vantage_cli.commands.license import license_app

        assert license_app.info.name == "license"
        assert "software licenses" in license_app.info.help.lower()

    def test_server_app_is_typer_instance(self):
        """Test that server_app is properly configured."""
        from vantage_cli.commands.license.server import server_app

        assert server_app.info.name == "server"
        assert "license servers" in server_app.info.help.lower()

    def test_product_app_is_typer_instance(self):
        """Test that product_app is properly configured."""
        from vantage_cli.commands.license.product import product_app

        assert product_app.info.name == "product"
        assert "license products" in product_app.info.help.lower()

    def test_configuration_app_is_typer_instance(self):
        """Test that configuration_app is properly configured."""
        from vantage_cli.commands.license.configuration import configuration_app

        assert configuration_app.info.name == "configuration"
        assert "license configurations" in configuration_app.info.help.lower()

    def test_deployment_app_is_typer_instance(self):
        """Test that deployment_app is properly configured."""
        from vantage_cli.commands.license.deployment import deployment_app

        assert deployment_app.info.name == "deployment"
        assert "license deployments" in deployment_app.info.help.lower()

    def test_license_subcommands_registered(self):
        """Test that all license subcommands are registered."""
        from vantage_cli.commands.license import license_app

        # License app uses registered_groups for typer subcommands
        assert len(license_app.registered_groups) == 4

        # Get the typer names from registered groups
        group_names = [group.name for group in license_app.registered_groups]

        assert "server" in group_names
        assert "product" in group_names
        assert "configuration" in group_names
        assert "deployment" in group_names

    def test_server_commands_registered(self):
        """Test that all server CRUD commands are registered."""
        from vantage_cli.commands.license.server import server_app

        registered_commands = [cmd.name for cmd in server_app.registered_commands]

        expected_commands = ["create", "delete", "get", "list", "update"]
        for cmd in expected_commands:
            assert cmd in registered_commands

    def test_product_commands_registered(self):
        """Test that all product CRUD commands are registered."""
        from vantage_cli.commands.license.product import product_app

        registered_commands = [cmd.name for cmd in product_app.registered_commands]

        expected_commands = ["create", "delete", "get", "list", "update"]
        for cmd in expected_commands:
            assert cmd in registered_commands

    def test_configuration_commands_registered(self):
        """Test that all configuration CRUD commands are registered."""
        from vantage_cli.commands.license.configuration import configuration_app

        registered_commands = [cmd.name for cmd in configuration_app.registered_commands]

        expected_commands = ["create", "delete", "get", "list", "update"]
        for cmd in expected_commands:
            assert cmd in registered_commands

    def test_deployment_commands_registered(self):
        """Test that all deployment CRUD commands are registered."""
        from vantage_cli.commands.license.deployment import deployment_app

        registered_commands = [cmd.name for cmd in deployment_app.registered_commands]

        expected_commands = ["create", "delete", "get", "list", "update"]
        for cmd in expected_commands:
            assert cmd in registered_commands
