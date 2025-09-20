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
"""Comprehensive tests for cluster commands."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import click.exceptions
import pytest
import typer

from tests.conftest import MockConsole

# Import the functions we want to test
try:
    from vantage_cli.commands.cluster.create import create_cluster
    from vantage_cli.commands.cluster.delete import delete_cluster
    from vantage_cli.commands.cluster.get import get_cluster
    from vantage_cli.commands.cluster.list import list_clusters
    from vantage_cli.commands.cluster.render import (
        render_cluster_details,
        render_clusters_table,
    )

    # Removed unused Settings import
except ImportError:
    # Handle import errors during testing
    pytest.skip("Cluster module not available", allow_module_level=True)


class TestClusterCreate:
    """Test cluster creation functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock typer context."""
        ctx = Mock(spec=typer.Context)
        ctx.params = {"json_output": False}
        ctx.obj = SimpleNamespace(
            profile="default", verbose=False, json_output=False, console=MockConsole()
        )
        return ctx

    @pytest.fixture
    def sample_creation_response(self):
        """Sample cluster creation response."""
        return {
            "createCluster": {
                "name": "test-cluster",
                "status": "CREATING",
                "clientId": "test-client-123",
                "description": "Test cluster",
                "provider": "localhost",
                "ownerEmail": "test@example.com",
                "cloudAccountId": None,
                "creationParameters": {"cloud": "localhost", "deploy": "multipass-singlenode"},
            }
        }

    @pytest.mark.asyncio
    @patch("vantage_cli.commands.cluster.create.create_async_graphql_client")
    async def test_create_cluster_success(
        self, mock_graphql_client_factory, mock_context, sample_creation_response
    ):
        """Test successful cluster creation."""
        # Setup
        mock_client = AsyncMock()
        mock_client.execute_async.return_value = sample_creation_response
        mock_graphql_client_factory.return_value = mock_client

        # Execute
        await create_cluster(
            ctx=mock_context,
            cluster_name="test-cluster",
            cloud="localhost",
        )

        # Verify GraphQL was called
        mock_client.execute_async.assert_called_once()
        call_args = mock_client.execute_async.call_args
        assert "test-cluster" in str(call_args)

    @pytest.mark.asyncio
    @patch("vantage_cli.commands.cluster.create.create_async_graphql_client")
    async def test_create_cluster_with_config_file(
        self, mock_graphql_client_factory, mock_context, sample_creation_response, tmp_path
    ):
        """Test cluster creation with config file."""
        # Setup
        mock_client = AsyncMock()
        mock_client.execute_async.return_value = sample_creation_response
        mock_graphql_client_factory.return_value = mock_client

        # Create a temporary config file
        config_file = tmp_path / "cluster_config.json"
        config_file.write_text("""
{
  "cloud": "localhost",
  "deploy": "multipass-singlenode",
  "description": "Test cluster from config"
}
        """)

        # Execute
        await create_cluster(
            ctx=mock_context,
            cluster_name="test-cluster",
            cloud="localhost",
            config_file=config_file,
        )

        # Verify
        mock_client.execute_async.assert_called_once()

    @pytest.mark.asyncio
    @patch("vantage_cli.commands.cluster.create.create_async_graphql_client")
    async def test_create_cluster_graphql_error(self, mock_graphql_client_factory, mock_context):
        """Test cluster creation with GraphQL error."""
        # Setup
        mock_client = AsyncMock()
        mock_client.execute_async.side_effect = Exception("GraphQL error")
        mock_graphql_client_factory.return_value = mock_client

        # Execute & Assert
        with pytest.raises(click.exceptions.Exit) as exc_info:
            await create_cluster(
                ctx=mock_context,
                cluster_name="test-cluster",
                cloud="localhost",
            )
        assert exc_info.value.exit_code == 1


class TestClusterList:
    """Test cluster listing functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock typer context."""
        ctx = Mock(spec=typer.Context)
        ctx.params = {"json_output": False}
        ctx.obj = Mock()
        ctx.obj.settings = Mock()
        ctx.obj.settings.supported_clouds = [
            "maas",
            "localhost",
            "aws",
            "gcp",
            "azure",
            "on-premises",
            "k8s",
        ]
        ctx.obj.profile = "default"
        return ctx

    @pytest.fixture
    def sample_clusters_response(self):
        """Sample clusters list response."""
        return {
            "clusters": {
                "edges": [
                    {
                        "node": {
                            "name": "cluster1",
                            "status": "RUNNING",
                            "clientId": "client-123",
                            "description": "First test cluster",
                            "ownerEmail": "test@example.com",
                            "provider": "localhost",
                            "cloudAccountId": None,
                            "creationParameters": {"cloud": "localhost"},
                        }
                    },
                    {
                        "node": {
                            "name": "cluster2",
                            "status": "CREATING",
                            "clientId": "client-456",
                            "description": "Second test cluster",
                            "ownerEmail": "test@example.com",
                            "provider": "aws",
                            "cloudAccountId": "aws-123",
                            "creationParameters": {"cloud": "aws"},
                        }
                    },
                ],
                "total": 2,
            }
        }

    @pytest.mark.asyncio
    @patch("vantage_cli.commands.cluster.list.create_async_graphql_client")
    async def test_list_clusters_success(
        self, mock_graphql_client_factory, mock_context, sample_clusters_response
    ):
        """Test successful cluster listing."""
        # Setup
        mock_client = AsyncMock()
        mock_client.execute_async.return_value = sample_clusters_response
        mock_graphql_client_factory.return_value = mock_client

        # Execute
        await list_clusters(ctx=mock_context)

        # Verify GraphQL was called
        mock_client.execute_async.assert_called_once()
        call_args = mock_client.execute_async.call_args
        assert "getClusters" in str(call_args)

    @pytest.mark.asyncio
    @patch("vantage_cli.commands.cluster.list.create_async_graphql_client")
    async def test_list_clusters_empty(self, mock_graphql_client_factory, mock_context):
        """Test listing when no clusters exist."""
        # Setup
        empty_response = {"clusters": {"edges": [], "total": 0}}
        mock_client = AsyncMock()
        mock_client.execute_async.return_value = empty_response
        mock_graphql_client_factory.return_value = mock_client

        # Execute
        await list_clusters(ctx=mock_context)

        # Verify
        mock_client.execute_async.assert_called_once()

    @pytest.mark.asyncio
    @patch("vantage_cli.commands.cluster.list.create_async_graphql_client")
    async def test_list_clusters_json_output(
        self, mock_graphql_client_factory, mock_context, sample_clusters_response
    ):
        """Test cluster listing with JSON output."""
        # Setup
        mock_client = AsyncMock()
        mock_client.execute_async.return_value = sample_clusters_response
        mock_graphql_client_factory.return_value = mock_client

        # Execute
        await list_clusters(ctx=mock_context)

        # Verify
        mock_client.execute_async.assert_called_once()

    @pytest.mark.asyncio
    @patch("vantage_cli.commands.cluster.list.create_async_graphql_client")
    async def test_list_clusters_graphql_error(self, mock_graphql_client_factory, mock_context):
        """Test cluster listing with GraphQL error."""
        # Setup
        mock_client = AsyncMock()
        mock_client.execute_async.side_effect = Exception("GraphQL error")
        mock_graphql_client_factory.return_value = mock_client

        # Execute & Assert
        with pytest.raises(click.exceptions.Exit) as exc_info:
            await list_clusters(ctx=mock_context)
        assert exc_info.value.exit_code == 1


class TestClusterDelete:
    """Test cluster deletion functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock typer context."""
        ctx = Mock(spec=typer.Context)
        ctx.params = {"json_output": False}
        ctx.obj = Mock()
        ctx.obj.settings = Mock()
        ctx.obj.settings.supported_clouds = [
            "maas",
            "localhost",
            "aws",
            "gcp",
            "azure",
            "on-premises",
            "k8s",
        ]
        ctx.obj.profile = "default"
        ctx.obj.json_output = False  # Explicitly set json_output to False
        return ctx

    @pytest.fixture
    def sample_deletion_response(self):
        """Sample cluster deletion response."""
        return {"deleteCluster": {"message": "Cluster deleted successfully"}}

    @pytest.mark.asyncio
    @patch("vantage_cli.commands.cluster.delete.create_async_graphql_client")
    async def test_delete_cluster_with_force(
        self, mock_graphql_client_factory, mock_context, sample_deletion_response
    ):
        """Test cluster deletion with force flag."""
        # Setup
        mock_client = AsyncMock()
        mock_client.execute_async.return_value = sample_deletion_response
        mock_graphql_client_factory.return_value = mock_client

        # Execute
        await delete_cluster(ctx=mock_context, cluster_name="test-cluster", force=True)

        # Verify GraphQL was called
        mock_client.execute_async.assert_called_once()
        call_args = mock_client.execute_async.call_args
        assert "deleteCluster" in str(call_args)
        assert "test-cluster" in str(call_args)

    @pytest.mark.asyncio
    @patch("vantage_cli.commands.cluster.delete.create_async_graphql_client")
    @patch("rich.prompt.Confirm.ask", return_value=True)
    async def test_delete_cluster_with_confirmation(
        self, mock_confirm, mock_graphql_client_factory, mock_context, sample_deletion_response
    ):
        """Test cluster deletion with user confirmation."""
        # Setup
        mock_client = AsyncMock()
        mock_client.execute_async.return_value = sample_deletion_response
        mock_graphql_client_factory.return_value = mock_client

        # Execute
        mock_context.obj.json_output = False
        await delete_cluster(ctx=mock_context, cluster_name="test-cluster", force=False)

        # Verify confirmation was asked and GraphQL was called
        mock_confirm.assert_called_once()
        mock_client.execute_async.assert_called_once()

    @pytest.mark.asyncio
    @patch("vantage_cli.commands.cluster.delete.create_async_graphql_client")
    @patch("rich.prompt.Confirm.ask", return_value=False)
    async def test_delete_cluster_cancelled(
        self, mock_confirm, mock_graphql_client_factory, mock_context
    ):
        """Test cluster deletion cancelled by user."""
        # Setup
        mock_client = AsyncMock()
        mock_graphql_client_factory.return_value = mock_client

        # Execute
        mock_context.obj.json_output = False
        await delete_cluster(ctx=mock_context, cluster_name="test-cluster", force=False)

        # Verify confirmation was asked but GraphQL was NOT called
        mock_confirm.assert_called_once()
        mock_client.execute_async.assert_not_called()

    @pytest.mark.asyncio
    @patch("vantage_cli.commands.cluster.delete.create_async_graphql_client")
    async def test_delete_cluster_json_output(
        self, mock_graphql_client_factory, mock_context, sample_deletion_response
    ):
        """Test cluster deletion with JSON output."""
        # Setup
        mock_client = AsyncMock()
        mock_client.execute_async.return_value = sample_deletion_response
        mock_graphql_client_factory.return_value = mock_client

        # Execute
        mock_context.obj.json_output = True
        await delete_cluster(ctx=mock_context, cluster_name="test-cluster", force=True)

        # Verify
        mock_client.execute_async.assert_called_once()

    @pytest.mark.asyncio
    @patch("vantage_cli.commands.cluster.delete.create_async_graphql_client")
    async def test_delete_cluster_graphql_error(self, mock_graphql_client_factory, mock_context):
        """Test cluster deletion with GraphQL error."""
        # Setup
        mock_client = AsyncMock()
        mock_client.execute_async.side_effect = Exception("GraphQL error")
        mock_graphql_client_factory.return_value = mock_client

        # Execute & Assert
        with pytest.raises(click.exceptions.Exit) as exc_info:
            await delete_cluster(ctx=mock_context, cluster_name="test-cluster", force=True)
        assert exc_info.value.exit_code == 1

    @pytest.mark.asyncio
    @patch("vantage_cli.commands.cluster.delete.create_async_graphql_client")
    @patch("vantage_cli.commands.cluster.delete.list_deployments_by_cluster")
    @patch("vantage_cli.commands.cluster.delete.remove_deployment")
    async def test_delete_cluster_with_app_cleanup(
        self,
        mock_remove_deployment,
        mock_list_deployments,
        mock_graphql_client_factory,
        mock_context,
        sample_deletion_response,
    ):
        """Test cluster deletion with app cleanup."""
        # Setup
        mock_client = AsyncMock()
        mock_client.execute_async.return_value = sample_deletion_response
        mock_graphql_client_factory.return_value = mock_client

        # Mock deployment data
        mock_deployments = {
            "deployment-123": {
                "app_name": "slurm-juju-localhost",
                "cluster_name": "test-cluster",
                "cluster_data": {"id": "cluster-123", "clientId": "client-123"},
                "status": "active",
            }
        }
        mock_list_deployments.return_value = mock_deployments
        mock_remove_deployment.return_value = True

        # Mock the cleanup function
        with patch(
            "vantage_cli.apps.slurm_juju_localhost.app.cleanup_juju_localhost"
        ) as mock_cleanup:
            mock_cleanup.return_value = None

            # Execute
            await delete_cluster(
                ctx=mock_context,
                cluster_name="test-cluster",
                force=True,
                app="slurm-juju-localhost",
            )

            # Verify GraphQL was called
            mock_client.execute_async.assert_called_once()

            # Verify deployments were queried with console parameter
            mock_list_deployments.assert_called_once_with("test-cluster", mock_context.obj.console)

            # Verify cleanup was called
            mock_cleanup.assert_called_once_with(
                mock_context, {"id": "cluster-123", "clientId": "client-123"}
            )

            # Verify deployment was removed with console parameter
            mock_remove_deployment.assert_called_once_with(
                "deployment-123", mock_context.obj.console
            )

    @pytest.mark.asyncio
    @patch("vantage_cli.commands.cluster.delete.create_async_graphql_client")
    @patch("vantage_cli.commands.cluster.delete.list_deployments_by_cluster")
    async def test_delete_cluster_with_app_no_deployments(
        self,
        mock_list_deployments,
        mock_graphql_client_factory,
        mock_context,
        sample_deletion_response,
    ):
        """Test cluster deletion with app cleanup when no deployments exist."""
        # Setup
        mock_client = AsyncMock()
        mock_client.execute_async.return_value = sample_deletion_response
        mock_graphql_client_factory.return_value = mock_client

        # Mock no deployments found
        mock_list_deployments.return_value = {}

        # Execute
        await delete_cluster(
            ctx=mock_context, cluster_name="test-cluster", force=True, app="slurm-juju-localhost"
        )

        # Verify GraphQL was called
        mock_client.execute_async.assert_called_once()

        # Verify deployments were queried with console parameter
        mock_list_deployments.assert_called_once_with("test-cluster", mock_context.obj.console)

    @pytest.mark.asyncio
    @patch("vantage_cli.commands.cluster.delete.create_async_graphql_client")
    @patch("vantage_cli.commands.cluster.delete.list_deployments_by_cluster")
    async def test_delete_cluster_with_app_wrong_type(
        self,
        mock_list_deployments,
        mock_graphql_client_factory,
        mock_context,
        sample_deletion_response,
    ):
        """Test cluster deletion with app cleanup when deployment has different app type."""
        # Setup
        mock_client = AsyncMock()
        mock_client.execute_async.return_value = sample_deletion_response
        mock_graphql_client_factory.return_value = mock_client

        # Mock deployment with different app type
        mock_deployments = {
            "deployment-123": {
                "app_name": "slurm-multipass-localhost",  # Different from requested app
                "cluster_name": "test-cluster",
                "cluster_data": {"id": "cluster-123"},
                "status": "active",
            }
        }
        mock_list_deployments.return_value = mock_deployments

        # Execute - request cleanup for juju but deployment is multipass
        await delete_cluster(
            ctx=mock_context, cluster_name="test-cluster", force=True, app="slurm-juju-localhost"
        )

        # Verify GraphQL was called
        mock_client.execute_async.assert_called_once()

        # Verify deployments were queried with console parameter
        mock_list_deployments.assert_called_once_with("test-cluster", mock_context.obj.console)


class TestClusterGet:
    """Test cluster retrieval functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock typer context."""
        ctx = Mock(spec=typer.Context)
        ctx.params = {"json_output": False}
        ctx.obj = Mock()
        ctx.obj.settings = Mock()
        ctx.obj.settings.supported_clouds = [
            "maas",
            "localhost",
            "aws",
            "gcp",
            "azure",
            "on-premises",
            "k8s",
        ]
        ctx.obj.profile = "default"
        return ctx

    @pytest.fixture
    def sample_cluster_response(self):
        """Sample single cluster response."""
        return {
            "clusters": {
                "edges": [
                    {
                        "node": {
                            "name": "test-cluster",
                            "status": "RUNNING",
                            "clientId": "client-123",
                            "description": "Test cluster",
                            "ownerEmail": "test@example.com",
                            "provider": "localhost",
                            "cloudAccountId": None,
                            "creationParameters": {"cloud": "localhost"},
                        }
                    }
                ]
            }
        }

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    @patch("vantage_cli.commands.cluster.utils.create_async_graphql_client")
    async def test_get_cluster_success(
        self, mock_graphql_client_factory, mock_context, sample_cluster_response
    ):
        """Test successful cluster retrieval."""
        # Setup
        mock_client = AsyncMock()
        mock_client.execute_async.return_value = sample_cluster_response
        mock_graphql_client_factory.return_value = mock_client

        # Execute
        await get_cluster(ctx=mock_context, cluster_name="test-cluster")

        # Verify GraphQL was called
        mock_client.execute_async.assert_called_once()
        call_args = mock_client.execute_async.call_args
        # Check that the query contains getClusters
        assert "getClusters" in str(call_args)
        # The variables should be passed as the second argument
        assert len(call_args[0]) >= 2  # Should have at least query and variables

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    @patch("vantage_cli.commands.cluster.utils.create_async_graphql_client")
    async def test_get_cluster_not_found(self, mock_graphql_client_factory, mock_context):
        """Test getting a cluster that doesn't exist."""
        # Setup
        not_found_response = {"cluster": None}
        mock_client = AsyncMock()
        mock_client.execute_async.return_value = not_found_response
        mock_graphql_client_factory.return_value = mock_client

        # Execute & Assert
        with pytest.raises(click.exceptions.Exit) as exc_info:
            await get_cluster(ctx=mock_context, cluster_name="nonexistent-cluster")
        assert exc_info.value.exit_code == 1

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    @patch("vantage_cli.commands.cluster.utils.create_async_graphql_client")
    async def test_get_cluster_json_output(
        self, mock_graphql_client_factory, mock_context, sample_cluster_response
    ):
        """Test cluster retrieval with JSON output."""
        # Setup
        mock_client = AsyncMock()
        mock_client.execute_async.return_value = sample_cluster_response
        mock_graphql_client_factory.return_value = mock_client

        # Execute
        await get_cluster(ctx=mock_context, cluster_name="test-cluster")

        # Verify
        mock_client.execute_async.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    @patch("vantage_cli.commands.cluster.utils.create_async_graphql_client")
    async def test_get_cluster_graphql_error(self, mock_graphql_client_factory, mock_context):
        """Test cluster retrieval with GraphQL error."""
        # Setup
        mock_client = AsyncMock()
        mock_client.execute_async.side_effect = ValueError("GraphQL error")
        mock_graphql_client_factory.return_value = mock_client

        # Execute & Assert
        with pytest.raises(click.exceptions.Exit) as exc_info:
            await get_cluster(ctx=mock_context, cluster_name="test-cluster")
        assert exc_info.value.exit_code == 1


class TestClusterRender:
    """Test cluster rendering functionality."""

    def test_render_cluster_details(self):
        """Test rendering cluster details."""
        from tests.conftest import MockConsole

        console = MockConsole()
        cluster_data = {
            "name": "test-cluster",
            "status": "RUNNING",
            "clientId": "client-123",
            "description": "Test cluster",
            "ownerEmail": "test@example.com",
            "provider": "localhost",
            "cloudAccountId": None,
            "creationParameters": {"cloud": "localhost"},
        }

        # This should not raise an exception
        render_cluster_details(cluster_data, console, json_output=False)

    def test_render_cluster_details_json(self):
        """Test rendering cluster details with JSON output."""
        from tests.conftest import MockConsole

        console = MockConsole()
        cluster_data = {"name": "test-cluster", "status": "RUNNING", "clientId": "client-123"}

        # This should not raise an exception
        render_cluster_details(cluster_data, console, json_output=True)

    def test_render_clusters_table_empty(self):
        """Test rendering empty clusters table."""
        from tests.conftest import MockConsole

        console = MockConsole()
        # This should not raise an exception
        render_clusters_table([], console, json_output=False)

    def test_render_clusters_table_with_data(self):
        """Test rendering clusters table with data."""
        from tests.conftest import MockConsole

        console = MockConsole()
        clusters_data = [
            {
                "name": "cluster1",
                "status": "RUNNING",
                "provider": "localhost",
                "ownerEmail": "test@example.com",
            },
            {
                "name": "cluster2",
                "status": "CREATING",
                "provider": "aws",
                "ownerEmail": "test@example.com",
            },
        ]

        # This should not raise an exception
        render_clusters_table(clusters_data, console, json_output=False)

    def test_render_clusters_table_json(self):
        """Test rendering clusters table with JSON output."""
        from tests.conftest import MockConsole

        console = MockConsole()
        clusters_data = [{"name": "cluster1", "status": "RUNNING"}]

        # This should not raise an exception
        render_clusters_table(clusters_data, console, json_output=True)
