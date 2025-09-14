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
"""Tests for the deployment create command."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
import typer

from vantage_cli.commands.deployment.create import create_deployment


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
def mock_ctx():
    """Mock typer context."""
    ctx = Mock(spec=typer.Context)
    # Mock the obj attribute with profile for @attach_settings decorator
    ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=False)
    return ctx


class TestCreateDeployment:
    """Tests for the create_deployment function."""

    @pytest.mark.asyncio
    @patch("vantage_cli.commands.deployment.create.get_available_apps")
    @patch("vantage_cli.commands.deployment.create.track_deployment")
    @patch("vantage_cli.commands.deployment.create.generate_default_deployment_name")
    @patch("uuid.uuid4")
    async def test_create_deployment_with_dev_run(
        self,
        mock_uuid4,
        mock_generate_name,
        mock_track_deployment,
        mock_get_available_apps,
        mock_config_file,
        mock_ctx,
    ):
        """Test create_deployment with --dev-run flag."""
        # Setup mocks
        mock_deployment_id = "test-deployment-id-12345"
        mock_uuid4.return_value = mock_deployment_id
        mock_generate_name.return_value = "slurm-multipass-localhost-test-cluster-20250914-123456"

        mock_deploy_func = AsyncMock()
        mock_get_available_apps.return_value = {
            "slurm-multipass-localhost": {
                "module": Mock(),
                "deploy_function": mock_deploy_func,
            }
        }

        # Test deployment creation with dev-run
        await create_deployment(
            ctx=mock_ctx,
            app_name="slurm-multipass-localhost",
            cluster_name="test-cluster",
            dev_run=True,
            name=None,
        )

        # Verify tracking was called
        mock_track_deployment.assert_called_once()

        # Verify deploy function was called
        mock_deploy_func.assert_called_once()

    @pytest.mark.asyncio
    @patch("vantage_cli.commands.deployment.create.get_available_apps")
    @patch("vantage_cli.commands.deployment.create.track_deployment")
    @patch("uuid.uuid4")
    async def test_create_deployment_with_custom_name(
        self,
        mock_uuid4,
        mock_track_deployment,
        mock_get_available_apps,
        mock_config_file,
        mock_ctx,
    ):
        """Test create_deployment with custom --name parameter."""
        # Setup mocks
        mock_deployment_id = "test-deployment-id-67890"
        mock_uuid4.return_value = mock_deployment_id
        custom_name = "my-custom-deployment"

        mock_deploy_func = AsyncMock()
        mock_get_available_apps.return_value = {
            "slurm-multipass-localhost": {
                "module": Mock(),
                "deploy_function": mock_deploy_func,
            }
        }

        # Test deployment creation with custom name
        await create_deployment(
            ctx=mock_ctx,
            app_name="slurm-multipass-localhost",
            cluster_name="test-cluster",
            dev_run=True,
            name=custom_name,
        )

        # Verify tracking was called
        mock_track_deployment.assert_called_once()

    @pytest.mark.asyncio
    @patch("vantage_cli.commands.deployment.create.get_available_apps")
    @patch("vantage_cli.commands.deployment.create.track_deployment")
    @patch("uuid.uuid4")
    async def test_create_deployment_invalid_app(
        self,
        mock_uuid4,
        mock_track_deployment,
        mock_get_available_apps,
        mock_config_file,
        mock_ctx,
    ):
        """Test create_deployment with invalid app name."""
        # Setup mocks
        mock_deployment_id = "test-deployment-id-invalid"
        mock_uuid4.return_value = mock_deployment_id
        mock_get_available_apps.return_value = {}  # No available apps

        # Test deployment creation with invalid app
        with pytest.raises(typer.Exit):
            await create_deployment(
                ctx=mock_ctx,
                app_name="invalid-app",
                cluster_name="test-cluster",
                dev_run=True,
                name=None,
            )

        # Verify tracking was NOT called for invalid app
        mock_track_deployment.assert_not_called()

    @pytest.mark.asyncio
    @patch("vantage_cli.commands.deployment.create.get_available_apps")
    @patch("vantage_cli.commands.deployment.create.generate_dev_cluster_data")
    async def test_create_deployment_dev_cluster_data_generation(
        self,
        mock_generate_dev_data,
        mock_get_available_apps,
        mock_config_file,
        mock_ctx,
    ):
        """Test that dev cluster data is generated correctly for dev_run."""
        mock_dev_cluster_data = {
            "name": "test-cluster",
            "clientId": "dev-client-12345",
            "clientSecret": "dev-secret-67890",
        }
        mock_generate_dev_data.return_value = mock_dev_cluster_data

        mock_deploy_func = AsyncMock()
        mock_get_available_apps.return_value = {
            "slurm-multipass-localhost": {
                "module": Mock(),
                "deploy_function": mock_deploy_func,
            }
        }

        # Mock UUID to avoid randomness
        with patch("uuid.uuid4") as mock_uuid:
            mock_uuid.return_value = "test-uuid"

            # Test deployment creation with dev_run
            await create_deployment(
                ctx=mock_ctx,
                app_name="slurm-multipass-localhost",
                cluster_name="test-cluster",
                dev_run=True,
                name=None,
            )

        # Verify dev cluster data was generated
        mock_generate_dev_data.assert_called_once_with("test-cluster")

        # Verify deploy function was called
        mock_deploy_func.assert_called_once()
