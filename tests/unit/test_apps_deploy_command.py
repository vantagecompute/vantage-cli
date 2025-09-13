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
"""Tests for the apps deploy command."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
import typer

from vantage_cli.commands.app.deploy import deploy_app


@pytest.fixture
def mock_config_file():
    """Mock config file for @attach_settings decorator."""
    with patch("vantage_cli.config.USER_CONFIG_FILE") as mock_config_file:
        mock_config_file.exists.return_value = True
        mock_config_file.read_text.return_value = json.dumps(
            {"default": {"api_base_url": "https://test.com"}}
        )
        yield mock_config_file


@pytest.fixture
def mock_ctx() -> typer.Context:
    """Mock typer context."""
    ctx = Mock(spec=typer.Context)
    # Mock the obj attribute with profile for @attach_settings decorator
    ctx.obj = Mock()
    ctx.obj.profile = "default"
    return ctx


@pytest.fixture
def mock_console():
    """Mock rich console."""
    with patch("vantage_cli.commands.app.deploy.console") as mock_console:
        yield mock_console


@pytest.fixture
def mock_cluster_data():
    """Mock cluster data."""
    return {
        "id": "cluster-123",
        "name": "test-cluster",
        "clientId": "client-123",
        "clientSecret": "secret-123",
    }


class TestDeployApp:
    """Tests for deploy_app function."""

    @pytest.mark.asyncio
    async def test_deploy_app_invalid_app_name(self, mock_ctx, mock_console, mock_config_file):
        """Test deploy_app with invalid app name."""
        with patch("vantage_cli.commands.app.deploy.get_available_apps") as mock_get_apps:
            mock_get_apps.return_value = {
                "slurm-juju-localhost": {"deploy_function": AsyncMock()},
                "slurm-multipass-localhost": {"deploy_function": AsyncMock()},
            }

            with pytest.raises(typer.Exit):
                await deploy_app(mock_ctx, "invalid-app", "test-cluster")

            # Verify error message was printed
            mock_console.print.assert_any_call(
                "[bold red]✗ App 'invalid-app' not found[/bold red]"
            )
            mock_console.print.assert_any_call(
                "\nAvailable apps: slurm-juju-localhost, slurm-multipass-localhost"
            )
            mock_console.print.assert_any_call(
                "Use [cyan]vantage apps list[/cyan] to see all available applications."
            )

    @pytest.mark.asyncio
    async def test_deploy_app_invalid_cluster_name(self, mock_ctx, mock_console, mock_config_file):
        """Test deploy_app with invalid cluster name."""
        with (
            patch("vantage_cli.commands.app.deploy.get_available_apps") as mock_get_apps,
            patch("vantage_cli.commands.app.deploy.get_cluster_by_name") as mock_get_cluster,
        ):
            mock_get_apps.return_value = {"slurm-juju-localhost": {"deploy_function": AsyncMock()}}
            mock_get_cluster.return_value = None

            with pytest.raises(typer.Exit):
                await deploy_app(mock_ctx, "slurm-juju-localhost", "invalid-cluster")

            # Verify cluster lookup was called
            mock_get_cluster.assert_called_once_with(mock_ctx, "invalid-cluster")

            # Verify error message was printed
            mock_console.print.assert_any_call(
                "[bold red]✗ Cluster 'invalid-cluster' not found[/bold red]"
            )

    @pytest.mark.asyncio
    async def test_deploy_app_function_based_success(
        self, mock_ctx, mock_console, mock_cluster_data, mock_config_file
    ):
        """Test successful deployment of function-based app."""
        mock_deploy_func = AsyncMock()

        with (
            patch("vantage_cli.commands.app.deploy.get_available_apps") as mock_get_apps,
            patch("vantage_cli.commands.app.deploy.get_cluster_by_name") as mock_get_cluster,
        ):
            mock_get_apps.return_value = {
                "slurm-juju-localhost": {"deploy_function": mock_deploy_func}
            }
            mock_get_cluster.return_value = mock_cluster_data

            await deploy_app(mock_ctx, "slurm-juju-localhost", "test-cluster")

            # Verify deploy function was called with correct arguments
            mock_deploy_func.assert_called_once_with(mock_ctx, mock_cluster_data)

            # Verify success message was printed
            mock_console.print.assert_any_call(
                "[bold blue]Deploying app 'slurm-juju-localhost' to cluster 'test-cluster'...[/bold blue]"
            )
            mock_console.print.assert_any_call(
                "[bold green]✓ App 'slurm-juju-localhost' deployed successfully to cluster 'test-cluster'![/bold green]"
            )

    @pytest.mark.asyncio
    async def test_deploy_app_no_deploy_function(
        self, mock_ctx, mock_console, mock_cluster_data, mock_config_file
    ):
        """Test deploy_app with app that has no deploy function."""
        with (
            patch("vantage_cli.commands.app.deploy.get_available_apps") as mock_get_apps,
            patch("vantage_cli.commands.app.deploy.get_cluster_by_name") as mock_get_cluster,
        ):
            mock_get_apps.return_value = {
                "broken-app": {"description": "An app without deploy function"}
            }
            mock_get_cluster.return_value = mock_cluster_data

            with pytest.raises(typer.Exit):
                await deploy_app(mock_ctx, "broken-app", "test-cluster")

            # Verify error message was printed
            mock_console.print.assert_any_call(
                "[bold red]✗ App 'broken-app' does not have a deploy function[/bold red]"
            )

    @pytest.mark.asyncio
    async def test_deploy_app_deploy_function_raises_exception(
        self, mock_ctx, mock_console, mock_cluster_data, mock_config_file
    ):
        """Test deploy_app when deploy function raises an exception."""
        mock_deploy_func = AsyncMock(side_effect=Exception("Deploy failed"))

        with (
            patch("vantage_cli.commands.app.deploy.get_available_apps") as mock_get_apps,
            patch("vantage_cli.commands.app.deploy.get_cluster_by_name") as mock_get_cluster,
        ):
            mock_get_apps.return_value = {"failing-app": {"deploy_function": mock_deploy_func}}
            mock_get_cluster.return_value = mock_cluster_data

            with pytest.raises(typer.Exit):
                await deploy_app(mock_ctx, "failing-app", "test-cluster")

            # Verify error message was printed
            mock_console.print.assert_any_call(
                "[bold red]✗ Error deploying app 'failing-app': Deploy failed[/bold red]"
            )

    @pytest.mark.asyncio
    async def test_deploy_app_deploy_function_raises_typer_exit(
        self, mock_ctx, mock_console, mock_cluster_data, mock_config_file
    ):
        """Test deploy_app when deploy function raises typer.Exit (should be re-raised)."""
        mock_deploy_func = AsyncMock(side_effect=typer.Exit(1))

        with (
            patch("vantage_cli.commands.app.deploy.get_available_apps") as mock_get_apps,
            patch("vantage_cli.commands.app.deploy.get_cluster_by_name") as mock_get_cluster,
        ):
            mock_get_apps.return_value = {"exit-app": {"deploy_function": mock_deploy_func}}
            mock_get_cluster.return_value = mock_cluster_data

            with pytest.raises(typer.Exit):
                await deploy_app(mock_ctx, "exit-app", "test-cluster")

            # Verify deploy function was called
            mock_deploy_func.assert_called_once_with(mock_ctx, mock_cluster_data)

    @pytest.mark.asyncio
    async def test_deploy_app_multiple_apps_available(
        self, mock_ctx, mock_console, mock_cluster_data, mock_config_file
    ):
        """Test deploy_app with multiple apps available."""
        mock_juju_deploy = AsyncMock()
        mock_multipass_deploy = AsyncMock()

        with (
            patch("vantage_cli.commands.app.deploy.get_available_apps") as mock_get_apps,
            patch("vantage_cli.commands.app.deploy.get_cluster_by_name") as mock_get_cluster,
        ):
            mock_get_apps.return_value = {
                "slurm-juju-localhost": {"deploy_function": mock_juju_deploy},
                "slurm-multipass-localhost": {"deploy_function": mock_multipass_deploy},
            }
            mock_get_cluster.return_value = mock_cluster_data

            # Test deploying multipass app
            await deploy_app(mock_ctx, "slurm-multipass-localhost", "test-cluster")

            # Verify only multipass deploy was called
            mock_multipass_deploy.assert_called_once_with(mock_ctx, mock_cluster_data)
            mock_juju_deploy.assert_not_called()

            # Verify success message
            mock_console.print.assert_any_call(
                "[bold green]✓ App 'slurm-multipass-localhost' deployed successfully to cluster 'test-cluster'![/bold green]"
            )
