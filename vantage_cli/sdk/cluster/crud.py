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

import logging
from typing import Any, Dict, List, Optional

import httpx
import typer

from vantage_cli.auth import extract_persona
from vantage_cli.exceptions import Abort
from vantage_cli.sdk.admin.management.organizations import get_extra_attributes
from vantage_cli.sdk.base import BaseGraphQLResourceSDK
from vantage_cli.sdk.cluster.schema import Cluster

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
            logger.debug(f"get: Raw data received for cluster '{resource_id}': {data}")

            # Extract cluster from GraphQL connection structure
            edges = data.get("clusters", {}).get("edges", [])

            if edges:
                cluster_data = edges[0]["node"]
                client_id = cluster_data.get("clientId", "")

                # Construct jupyterhub_url from settings and client_id
                base_domain = ".".join(ctx.obj.settings.vantage_url.split("//")[-1].split(".")[1:])
                jupyterhub_url = f"https://{client_id}.{base_domain}"

                # Convert to Cluster object
                return Cluster(
                    name=cluster_data.get("name", ""),
                    status=cluster_data.get("status", "unknown"),
                    client_id=client_id,
                    client_secret=cluster_data.get("clientSecret"),  # May be None
                    description=cluster_data.get("description", ""),
                    owner_email=cluster_data.get("ownerEmail", ""),
                    provider=cluster_data.get("provider", "unknown"),
                    cloud_account_id=cluster_data.get("cloudAccountId"),
                    creation_parameters=cluster_data.get("creationParameters", {}),
                    jupyterhub_url=jupyterhub_url,
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

        client_secret_from_api = None
        if (
            client_secret := await self.get_cluster_client_secret(
                ctx=ctx, client_id=result["clientId"]
            )
        ) is not None:
            client_secret_from_api = client_secret

        # SSSD binder password is required - must be set in organization extra attributes
        sssd_binder_password_from_api = None
        if (extra_attrs := await get_extra_attributes(ctx)) is not None:
            if (sssd_binder_password := extra_attrs.get("sssd_binder_password")) is not None:
                sssd_binder_password_from_api = sssd_binder_password
                logger.info(
                    "[dim]SSSD binder password retrieved from organization extra attributes[/dim]"
                )
            else:
                logger.error(
                    "[red]Error: SSSD binder password not found in organization extra attributes[/red]"
                )
                logger.warning(
                    "[yellow]Please contact your administrator to set the SSSD binder password in the organization settings[/yellow]"
                )
                raise typer.Exit(code=1)
        else:
            logger.error("[red]Error: Could not retrieve organization extra attributes[/red]")
            raise typer.Exit(code=1)

        client_id = result.get("clientId", "")

        # Construct jupyterhub_url from settings and client_id
        base_domain = ".".join(ctx.obj.settings.vantage_url.split("//")[-1].split(".")[1:])
        jupyterhub_url = f"https://{client_id}.{base_domain}"

        return Cluster(
            name=result.get("name", ""),
            status=result.get("status", "unknown"),
            client_id=client_id,
            client_secret=client_secret_from_api,
            description=result.get("description", ""),
            owner_email=result.get("ownerEmail", ""),
            provider=result.get("provider", "unknown"),
            cloud_account_id=result.get("cloudAccountId"),
            creation_parameters=result.get("creationParameters", {}),
            sssd_binder_password=sssd_binder_password_from_api,
            jupyterhub_url=jupyterhub_url,
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
        import logging

        logger = logging.getLogger(__name__)

        # Get raw cluster data from the base list method
        clusters_raw = await self.list(ctx, **kwargs)

        logger.debug(f"list_clusters: Got {len(clusters_raw)} raw clusters from API")
        if clusters_raw:
            logger.debug(f"list_clusters: First cluster sample: {clusters_raw[0]}")

        clusters: List[Cluster] = []
        for cluster_data in clusters_raw:
            try:
                client_id = cluster_data.get("clientId", "")

                # Construct jupyterhub_url from settings and client_id
                base_domain = ".".join(ctx.obj.settings.vantage_url.split("//")[-1].split(".")[1:])
                jupyterhub_url = f"https://{client_id}.{base_domain}"

                cluster = Cluster(
                    name=cluster_data.get("name", ""),
                    status=cluster_data.get("status", "unknown"),
                    client_id=client_id,
                    client_secret=cluster_data.get(
                        "clientSecret"
                    ),  # Will be None for list operations
                    description=cluster_data.get("description", ""),
                    owner_email=cluster_data.get("ownerEmail", ""),
                    provider=cluster_data.get("provider", "unknown"),
                    cloud_account_id=cluster_data.get("cloudAccountId"),
                    creation_parameters=cluster_data.get("creationParameters", {}),
                    jupyterhub_url=jupyterhub_url,
                )
                clusters.append(cluster)
            except Exception as e:
                # Skip clusters that fail to parse
                logger.warning(
                    f"list_clusters: Failed to parse cluster {cluster_data.get('name')}: {e}"
                )
                logger.debug(f"list_clusters: Cluster data that failed: {cluster_data}")
                continue

        logger.debug(f"list_clusters: Returning {len(clusters)} Cluster objects")
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

    async def get_cluster_client_secret(self, ctx: typer.Context, client_id: str) -> Optional[str]:
        """Get the client secret for the cluster from vantage-api using GraphQL client auth.

        Args:
            ctx: Typer context carrying settings/profile
            client_id: The client ID of the cluster

        Returns:
            The client secret if found, None otherwise
        """
        try:
            # Get user authentication using the same method as GraphQL client
            persona = extract_persona(ctx.obj.profile)
            access_token = persona.token_set.access_token

            # Use vantage-api admin/management/clients endpoint
            api_url = f"{ctx.obj.settings.get_apis_url()}/admin/management/clients"

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient() as client:
                # First, search for the client by clientId
                params = {"client_id": client_id}
                response = await client.get(api_url, headers=headers, params=params)

                if response.status_code != 200:
                    return None

                response_data = response.json()
                clients = response_data.get("clients", [])

                if not clients:
                    return None

                # Get the first matching client's internal ID
                vantage_client = clients[0]
                internal_id = vantage_client.get("id")

                if not internal_id:
                    return None

                # Get the client secret using the internal ID
                secret_url = f"{api_url}/{internal_id}"
                secret_response = await client.get(secret_url, headers=headers)

                if secret_response.status_code != 200:
                    return None

                secret_data = secret_response.json()
                # Try both camelCase and snake_case field names
                client_secret = secret_data.get("client_secret")

                return client_secret

        except Exception:
            return None

    async def get_cluster_by_name(self, ctx: typer.Context, cluster_name: str) -> Cluster | None:
        """Get cluster details by name with client secret populated.

        This method fetches the cluster from the API and then retrieves the client
        secret separately, populating it in the returned Cluster object.

        Args:
            ctx: Typer context carrying settings/profile
            cluster_name: The name of the cluster to retrieve

        Returns:
            The Cluster object if found (with client_secret populated), None otherwise
        """
        # Ensure we have settings configured
        if not ctx.obj or not ctx.obj.settings:
            raise Abort(
                "No settings configured. Please run 'vantage config set' first.",
                subject="Configuration Required",
                log_message="Settings not configured",
            )

        try:
            # Use the SDK to get the cluster
            cluster_obj = await self.get_cluster(ctx, cluster_name)

            if not cluster_obj:
                return None

            # Fetch client secret from API if clientId is available and update the cluster object
            client_id = cluster_obj.client_id
            if client_id:
                try:
                    client_secret = await self.get_cluster_client_secret(ctx, client_id)
                    if client_secret:
                        # Update the cluster object with the fetched secret
                        cluster_obj.client_secret = client_secret
                except Exception:
                    pass  # Keep the existing client_secret value (None)

            return cluster_obj

        except Abort:
            # Re-raise Abort exceptions as they contain user-friendly messages
            raise
        except Exception as e:
            raise Abort(
                f"Failed to retrieve cluster '{cluster_name}' from Vantage API.",
                subject="API Error",
                log_message=f"Cluster get error: {e}",
            )


# Create a singleton instance for use in commands
cluster_sdk = ClusterSDK()
