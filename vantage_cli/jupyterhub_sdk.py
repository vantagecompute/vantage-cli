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
"""JupyterHub SDK for notebook server management."""

import logging
from typing import Any, Dict, Optional

import typer

from vantage_cli.exceptions import Abort
from vantage_cli.jupyterhub_client import JupyterHubClient
from vantage_cli.sdk.cluster.crud import cluster_sdk

logger = logging.getLogger(__name__)


class JupyterHubSDK:
    """SDK for JupyterHub notebook server operations."""

    async def get_cluster_jupyterhub_client(
        self, ctx: typer.Context, cluster_name: str
    ) -> JupyterHubClient:
        """Get a JupyterHub client for a specific cluster.

        Args:
            ctx: Typer context
            cluster_name: Name of the cluster

        Returns:
            Configured JupyterHubClient instance

        Raises:
            Abort: If cluster not found or missing JupyterHub configuration
        """
        # Get cluster details
        cluster = await cluster_sdk.get_cluster(ctx, cluster_name)

        if not cluster:
            raise Abort(
                f"Cluster '{cluster_name}' not found",
                subject="Cluster Not Found",
                log_message=f"Cluster '{cluster_name}' not found",
            )

        # Get JupyterHub URL and token from cluster
        hub_url = cluster.jupyterhub_url
        hub_token = cluster.jupyterhub_token

        if not hub_url:
            raise Abort(
                f"Cluster '{cluster_name}' does not have a JupyterHub URL configured",
                subject="Missing JupyterHub URL",
                log_message=f"No jupyterhub_url in cluster '{cluster_name}' data",
            )

        if not hub_token:
            raise Abort(
                f"Cluster '{cluster_name}' does not have a JupyterHub token configured",
                subject="Missing JupyterHub Token",
                log_message=f"No jupyterhubToken in cluster '{cluster_name}' creation parameters",
            )

        logger.debug(f"Creating JupyterHub client for cluster '{cluster_name}' at {hub_url}")

        return JupyterHubClient(hub_url=hub_url, api_token=hub_token)

    async def create_notebook_server(
        self,
        ctx: typer.Context,
        cluster_name: str,
        username: str,
        server_name: Optional[str] = None,
        server_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a notebook server on a cluster.

        Args:
            ctx: Typer context
            cluster_name: Name of the cluster
            username: JupyterHub username
            server_name: Optional named server
            server_options: Optional server configuration

        Returns:
            Server creation response data

        Raises:
            Abort: If server creation fails
        """
        # Get JupyterHub client for the cluster
        hub_client = await self.get_cluster_jupyterhub_client(ctx, cluster_name)

        try:
            # Create the server
            result = await hub_client.create_user_server(
                username=username,
                server_name=server_name,
                options=server_options,
            )

            return {
                "cluster_name": cluster_name,
                "username": username,
                "server_name": server_name or "default",
                "status": result.get("status", "created"),
                "message": result.get("message", "Server created successfully"),
            }

        finally:
            await hub_client.close()

    async def get_notebook_server(
        self,
        ctx: typer.Context,
        cluster_name: str,
        username: str,
        server_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get information about a notebook server.

        Args:
            ctx: Typer context
            cluster_name: Name of the cluster
            username: JupyterHub username
            server_name: Optional named server

        Returns:
            Server information or None if not found
        """
        hub_client = await self.get_cluster_jupyterhub_client(ctx, cluster_name)

        try:
            server_info = await hub_client.get_user_server(
                username=username, server_name=server_name
            )

            if server_info:
                return {
                    "cluster_name": cluster_name,
                    "username": username,
                    "server_name": server_name or "default",
                    **server_info,
                }

            return None

        finally:
            await hub_client.close()

    async def stop_notebook_server(
        self,
        ctx: typer.Context,
        cluster_name: str,
        username: str,
        server_name: Optional[str] = None,
    ) -> bool:
        """Stop a notebook server.

        Args:
            ctx: Typer context
            cluster_name: Name of the cluster
            username: JupyterHub username
            server_name: Optional named server

        Returns:
            True if successful, False otherwise
        """
        hub_client = await self.get_cluster_jupyterhub_client(ctx, cluster_name)

        try:
            return await hub_client.stop_user_server(username=username, server_name=server_name)

        finally:
            await hub_client.close()

    async def list_cluster_users(
        self, ctx: typer.Context, cluster_name: str
    ) -> list[Dict[str, Any]]:
        """List all users on a cluster's JupyterHub.

        Args:
            ctx: Typer context
            cluster_name: Name of the cluster

        Returns:
            List of user data
        """
        hub_client = await self.get_cluster_jupyterhub_client(ctx, cluster_name)

        try:
            users = await hub_client.list_users()
            return [{"cluster_name": cluster_name, **user} for user in users]

        finally:
            await hub_client.close()


# Create singleton instance
jupyterhub_sdk = JupyterHubSDK()
