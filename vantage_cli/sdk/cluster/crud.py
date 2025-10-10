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

from vantage_cli.sdk.base import BaseGraphQLResourceSDK
from vantage_cli.sdk.cluster.schema import Cluster


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

    def _get_single_query(self) -> str:
        """Get the GraphQL query for fetching a single cluster.

        The GraphQL API supports filtering via the filters parameter. We use
        the name filter with an 'eq' operator to fetch a specific cluster.

        Returns:
            GraphQL query string for fetching a single cluster by name
        """
        return """
        query getClusters($first: Int!, $filters: JSONScalar) {
            clusters(first: $first, filters: $filters) {
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

    async def get(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, ctx: typer.Context, resource_id: str, **kwargs: Any
    ) -> Optional[Cluster]:
        """Get a specific cluster by name using GraphQL query with filtering.

        This method uses the GraphQL filters parameter to query for a specific
        cluster by name, which is more efficient than fetching all clusters.

        Args:
            ctx: Typer context with settings and console
            resource_id: Cluster name to retrieve
            **kwargs: Additional parameters

        Returns:
            Cluster object or None if not found
        """
        try:
            # Use GraphQL filters to query for specific cluster by name
            # Filter syntax: {"name": {"eq": "cluster-name"}}
            variables = {
                "first": 1,  # We only expect one result
                "filters": {"name": {"eq": resource_id}},
            }
            query = self._get_single_query()

            data = await self._execute_graphql_query(ctx, query, variables)

            # Extract cluster from GraphQL connection structure
            edges = data.get("clusters", {}).get("edges", [])

            if edges:
                cluster_data = edges[0]["node"]
                # Convert to Cluster object
                return Cluster(
                    name=cluster_data.get("name", ""),
                    status=cluster_data.get("status", "unknown"),
                    client_id=cluster_data.get("clientId", ""),
                    client_secret=cluster_data.get("clientSecret"),  # May be None
                    description=cluster_data.get("description", ""),
                    owner_email=cluster_data.get("ownerEmail", ""),
                    provider=cluster_data.get("provider", "unknown"),
                    cloud_account_id=cluster_data.get("cloudAccountId"),
                    creation_parameters=cluster_data.get("creationParameters", {}),
                )

            return None

        except Exception:
            # Re-raise to let the base class error handling deal with it
            raise

    def _get_create_mutation(self) -> str:
        """Get the GraphQL mutation for creating a cluster."""
        return """
        mutation createCluster($createClusterInput: CreateClusterInput!) {
            createCluster(createClusterInput: $createClusterInput) {
                ... on Cluster {
                    name
                    status
                    clientId
                    description
                    ownerEmail
                    provider
                    cloudAccountId
                    creationParameters
                }
                ... on ClusterNameInUse {
                    message
                }
                ... on InvalidInput {
                    message
                }
                ... on ClusterCouldNotBeDeployed {
                    message
                }
                ... on UnexpectedBehavior {
                    message
                }
            }
        }
        """

    async def create(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, ctx: typer.Context, resource_data: Dict[str, Any], **kwargs: Any
    ) -> Cluster:
        """Create a new cluster.

        Args:
            ctx: Typer context with settings and console
            resource_data: Dictionary containing cluster creation parameters:
                - name: Cluster name (required)
                - description: Cluster description (optional)
                - provider: Cloud provider (required) - "on_prem", "aws", etc.
                - providerAttributes: Provider-specific configuration (optional)
            **kwargs: Additional parameters

        Returns:
            Created Cluster object

        Raises:
            Exception: If cluster creation fails or name is already in use
        """
        mutation = self._get_create_mutation()
        variables = {"createClusterInput": resource_data}

        data = await self._execute_graphql_query(ctx, mutation, variables)
        result = data.get("createCluster", {})

        # Check for error responses
        if "message" in result and "name" not in result:
            error_message = result.get("message", "Unknown error")
            raise Exception(f"Failed to create cluster: {error_message}")

        # Convert to Cluster object
        return Cluster(
            name=result.get("name", ""),
            status=result.get("status", "unknown"),
            client_id=result.get("clientId", ""),
            client_secret=None,  # clientSecret not returned by API
            description=result.get("description", ""),
            owner_email=result.get("ownerEmail", ""),
            provider=result.get("provider", "unknown"),
            cloud_account_id=result.get("cloudAccountId"),
            creation_parameters=result.get("creationParameters", {}),
        )

    def _get_delete_mutation(self) -> str:
        """Get the GraphQL mutation for deleting a cluster."""
        return """
        mutation deleteCluster($clusterName: String!) {
            deleteCluster(clusterName: $clusterName) {
                ... on ClusterDeleted {
                    message
                }
                ... on ClusterNotFound {
                    message
                }
                ... on InvalidProviderInput {
                    message
                }
                ... on UnexpectedBehavior {
                    message
                }
            }
        }
        """

    async def update(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, ctx: typer.Context, resource_id: str, resource_data: Dict[str, Any], **kwargs: Any
    ) -> Cluster:
        """Update an existing cluster.

        Args:
            ctx: Typer context with settings and console
            resource_id: Cluster name to update
            resource_data: Dictionary containing fields to update
            **kwargs: Additional parameters

        Returns:
            Updated Cluster object

        Raises:
            NotImplementedError: Cluster updates are not currently supported by the GraphQL API

        Note: The Vantage GraphQL API does not currently support cluster updates.
        This method is included for API completeness but will raise NotImplementedError.
        """
        raise NotImplementedError(
            "Cluster updates are not currently supported by the Vantage API. "
            "To modify a cluster, you must delete and recreate it."
        )

    async def delete(self, ctx: typer.Context, resource_id: str, **kwargs: Any) -> bool:
        """Delete a cluster.

        Args:
            ctx: Typer context with settings and console
            resource_id: Cluster name to delete
            **kwargs: Additional parameters

        Returns:
            True if deletion was successful

        Raises:
            Exception: If cluster deletion fails or cluster not found
        """
        mutation = self._get_delete_mutation()
        variables = {"clusterName": resource_id}

        data = await self._execute_graphql_query(ctx, mutation, variables)
        result = data.get("deleteCluster", {})

        # Check for successful deletion
        if "ClusterDeleted" in str(type(result).__name__) or (
            "message" in result and "deleted" in result["message"].lower()
        ):
            return True

        # Check for error responses
        if "message" in result:
            error_message = result.get("message", "Unknown error")
            if "not found" in error_message.lower():
                raise Exception(f"Cluster not found: {resource_id}")
            raise Exception(f"Failed to delete cluster: {error_message}")

        return True

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
                    client_secret=cluster_data.get(
                        "clientSecret"
                    ),  # Will be None for list operations
                    description=cluster_data.get("description", ""),
                    owner_email=cluster_data.get("ownerEmail", ""),
                    provider=cluster_data.get("provider", "unknown"),
                    cloud_account_id=cluster_data.get("cloudAccountId"),
                    creation_parameters=cluster_data.get("creationParameters", {}),
                )
                clusters.append(cluster)
            except Exception:
                # Skip clusters that fail to parse
                continue

        return clusters

    async def get_cluster(
        self, ctx: typer.Context, cluster_name: str, **kwargs: Any
    ) -> Optional[Cluster]:
        """Get a specific cluster as a Cluster object.

        This is an alias for the get() method for consistency with list_clusters().

        Args:
            ctx: Typer context
            cluster_name: Name of the cluster to retrieve
            **kwargs: Additional parameters

        Returns:
            Cluster object or None if not found
        """
        return await self.get(ctx, cluster_name, **kwargs)

    async def create_cluster(
        self,
        ctx: typer.Context,
        name: str,
        provider: str,
        description: Optional[str] = None,
        provider_attributes: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Cluster:
        """Create a new cluster with simplified parameters.

        Args:
            ctx: Typer context
            name: Cluster name
            provider: Cloud provider ("on_prem", "aws", "gcp", "azure")
            description: Optional cluster description
            provider_attributes: Optional provider-specific configuration
            **kwargs: Additional parameters

        Returns:
            Created Cluster object

        Raises:
            Exception: If cluster creation fails
        """
        resource_data: Dict[str, Any] = {
            "name": name,
            "provider": provider,
            "description": description or f"Cluster {name} created via CLI",
        }

        if provider_attributes:
            resource_data["providerAttributes"] = provider_attributes

        return await self.create(ctx, resource_data, **kwargs)

    async def delete_cluster(self, ctx: typer.Context, cluster_name: str, **kwargs: Any) -> bool:
        """Delete a cluster by name.

        This is an alias for the delete() method for consistency with other cluster methods.

        Args:
            ctx: Typer context
            cluster_name: Name of the cluster to delete
            **kwargs: Additional parameters

        Returns:
            True if deletion was successful

        Raises:
            Exception: If cluster deletion fails
        """
        return await self.delete(ctx, cluster_name, **kwargs)


# Create a singleton instance for use in commands
cluster_sdk = ClusterSDK()
