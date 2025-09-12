# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Tests for storage and network commands."""


class TestStorageCommandStructure:
    """Test storage command structure and configuration."""

    def test_storage_app_is_typer_instance(self):
        """Test that storage_app is properly configured."""
        from vantage_cli.commands.storage import storage_app

        assert storage_app.info.name == "storage"
        assert "storage volumes" in storage_app.info.help.lower()

    def test_storage_commands_registered(self):
        """Test that all storage commands are registered."""
        from vantage_cli.commands.storage import storage_app

        registered_commands = [cmd.name for cmd in storage_app.registered_commands]

        expected_commands = ["attach", "create", "delete", "detach", "get", "list", "update"]
        for cmd in expected_commands:
            assert cmd in registered_commands


class TestNetworkCommandStructure:
    """Test network command structure and configuration."""

    def test_network_app_is_typer_instance(self):
        """Test that network_app is properly configured."""
        from vantage_cli.commands.network import network_app

        assert network_app.info.name == "network"
        assert "virtual networks" in network_app.info.help.lower()

    def test_network_commands_registered(self):
        """Test that all network commands are registered."""
        from vantage_cli.commands.network import network_app

        registered_commands = [cmd.name for cmd in network_app.registered_commands]

        expected_commands = ["attach", "create", "delete", "detach", "get", "list", "update"]
        for cmd in expected_commands:
            assert cmd in registered_commands


class TestMainAppIntegration:
    """Test integration with main application."""

    def test_storage_and_network_apps_registered_in_main(self):
        """Test that storage and network apps are registered in the main CLI."""
        from vantage_cli.main import app

        # Main app uses registered_groups for typer subcommands
        group_names = [group.name for group in app.registered_groups]

        assert "storage" in group_names
        assert "network" in group_names
