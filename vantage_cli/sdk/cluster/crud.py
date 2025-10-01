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
"""Cluster CRUD SDK using the base CRUD classes."""

from typing import Any, Dict, List, Optional

import typer

from vantage_cli.schemas import Cluster
from vantage_cli.sdk.base import BaseGraphQLResourceSDK


class ClusterSDK(BaseGraphQLResourceSDK):
    """SDK for cluster CRUD operations using GraphQL API."""

    def __init__(self):
        super().__init__(resource_name="cluster")

    def _get_list_query(self) -> str:
        """Get the GraphQL query for listing clusters."""
        return """
        query getClusters($first: Int!) {
            clusters(first: $first) {
                edges {
                    node {
                        name
                        status
                        clientId
                        description
                        ownerEmail
                        provider
                        cloudAccountId
                        creationParameters
                    }
                }
            }
        }
        """

    async def create(
        self, ctx: typer.Context, resource_data: Dict[str, Any], **kwargs: Any
    ) -> Dict[str, Any]:
        """Create a new cluster.

        Note: Cluster creation is not yet implemented in the GraphQL API.
        This is a placeholder for future implementation.
        """
        raise NotImplementedError("Cluster creation is not yet implemented")

    async def update(
        self, ctx: typer.Context, resource_id: str, resource_data: Dict[str, Any], **kwargs: Any
    ) -> Dict[str, Any]:
        """Update an existing cluster.

        Note: Cluster updates are not yet implemented in the GraphQL API.
        This is a placeholder for future implementation.
        """
        raise NotImplementedError("Cluster updates are not yet implemented")

    async def delete(self, ctx: typer.Context, resource_id: str, **kwargs: Any) -> bool:
        """Delete a cluster.

        Note: Cluster deletion is not yet implemented in the GraphQL API.
        This is a placeholder for future implementation.
        """
        raise NotImplementedError("Cluster deletion is not yet implemented")

    async def list_clusters(self, ctx: typer.Context, **kwargs: Any) -> List[Cluster]:
        """List all clusters as Cluster objects.

        Args:
            ctx: Typer context
            **kwargs: Additional filtering parameters

        Returns:
            List of Cluster objects
        """
        # Get raw cluster data from the base list method
        clusters_raw = await self.list(ctx, **kwargs)

        clusters: List[Cluster] = []
        for cluster_data in clusters_raw:
            try:
                cluster = Cluster(
                    name=cluster_data.get("name", ""),
                    status=cluster_data.get("status", "unknown"),
                    client_id=cluster_data.get("clientId", ""),
                    description=cluster_data.get("description", ""),
                    owner_email=cluster_data.get("ownerEmail", ""),
                    provider=cluster_data.get("provider", "unknown"),
                    cloud_account_id=cluster_data.get("cloudAccountId"),
                    creation_parameters=cluster_data.get("creationParameters", {}),
                )
                clusters.append(cluster)
            except Exception as e:
                from loguru import logger

                logger.warning(f"Failed to parse cluster data: {e}")
                continue

        return clusters

    async def get_cluster(
        self, ctx: typer.Context, cluster_name: str, **kwargs: Any
    ) -> Optional[Cluster]:
        """Get a specific cluster as a Cluster object.

        Args:
            ctx: Typer context
            cluster_name: Name of the cluster to retrieve
            **kwargs: Additional parameters

        Returns:
            Cluster object or None if not found
        """
        # Get raw cluster data from the base get method
        cluster_data = await self.get(ctx, cluster_name, **kwargs)

        if not cluster_data:
            return None

        try:
            return Cluster(
                name=cluster_data.get("name", ""),
                status=cluster_data.get("status", "unknown"),
                client_id=cluster_data.get("clientId", ""),
                description=cluster_data.get("description", ""),
                owner_email=cluster_data.get("ownerEmail", ""),
                provider=cluster_data.get("provider", "unknown"),
                cloud_account_id=cluster_data.get("cloudAccountId"),
                creation_parameters=cluster_data.get("creationParameters", {}),
            )
        except Exception as e:
            from loguru import logger

            logger.error(f"Failed to parse cluster data for '{cluster_name}': {e}")
            return None


# Create a singleton instance for use in commands
cluster_sdk = ClusterSDK()
