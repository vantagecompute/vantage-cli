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
"""Shared utilities for cluster commands."""

import textwrap
from typing import Any, Dict, Optional

import httpx
import typer
from loguru import logger

from vantage_cli.apps.utils import get_available_apps
from vantage_cli.auth import extract_persona
from vantage_cli.config import Settings
from vantage_cli.exceptions import Abort
from vantage_cli.gql_client import create_async_graphql_client


def get_cloud_choices() -> list[str]:
    """Get the list of supported clouds from settings."""
    settings = Settings()
    return settings.supported_clouds


def get_app_choices() -> list[str]:
    """Get the list of available deployment apps."""
    try:
        apps = get_available_apps()
        return list(apps.keys())
    except Exception as e:
        logger.warning(f"Failed to get available apps: {e}")
        return []


async def get_cluster_client_secret(ctx: typer.Context, client_id: str) -> Optional[str]:
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
        api_url = f"{ctx.obj.settings.api_base_url}/admin/management/clients"

        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

        async with httpx.AsyncClient() as client:
            # First, search for the client by clientId
            params = {"client_id": client_id}
            logger.debug(f"Searching for client with ID: {client_id} at {api_url}")
            response = await client.get(api_url, headers=headers, params=params)

            if response.status_code != 200:
                logger.error(
                    f"Failed to query vantage-api clients: {response.status_code} - {response.text}"
                )
                return None

            response_data = response.json()
            clients = response_data.get("clients", [])

            if not clients:
                logger.warning(f"No client found with clientId: {client_id}")
                return None

            # Get the first matching client's internal ID
            vantage_client = clients[0]
            internal_id = vantage_client.get("id")

            if not internal_id:
                logger.error(f"No internal ID found for client: {client_id}")
                return None

            # Get the client secret using the internal ID
            secret_url = f"{api_url}/{internal_id}"
            logger.debug(f"Fetching client secret from: {secret_url}")
            secret_response = await client.get(secret_url, headers=headers)

            if secret_response.status_code != 200:
                logger.error(
                    f"Failed to get client secret: {secret_response.status_code} - {secret_response.text}"
                )
                return None

            secret_data = secret_response.json()
            logger.debug(f"Client secret response data: {secret_data}")
            # Try both camelCase and snake_case field names
            client_secret = secret_data.get("client_secret")

            if client_secret:
                logger.debug(f"Successfully retrieved client secret for {client_id}")
            else:
                logger.warning(f"Client secret not found in response for {client_id}")
                logger.debug(f"Available keys in response: {list(secret_data.keys())}")

            return client_secret

    except Exception as e:
        logger.error(f"Error retrieving client secret for {client_id}: {e}")
        typer.Exit(code=1)


async def get_cluster_by_name(ctx: typer.Context, cluster_name: str) -> Dict[str, Any] | None:
    """Get cluster details by name from vantage-api using GraphQL client auth.

    Args:
        ctx: Typer context carrying settings/profile
        cluster_name: The name of the cluster to retrieve

    Returns:
        The cluster data if found, None otherwise
    """
    # Ensure we have settings configured
    if not ctx.obj or not ctx.obj.settings:
        raise Abort(
            "No settings configured. Please run 'vantage config set' first.",
            subject="Configuration Required",
            log_message="Settings not configured",
        )

    query = textwrap.dedent("""\
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
        """)

    variables = {"first": 100}  # Fetch up to 100 clusters

    try:
        # Create async GraphQL client
        graphql_client = create_async_graphql_client(ctx.obj.settings, ctx.obj.profile)

        # Execute the query
        logger.debug(f"Executing cluster get query for: {cluster_name}")
        response_data = await graphql_client.execute_async(query, variables)

        # Extract cluster data
        clusters_data = response_data.get("clusters", {})
        clusters = [edge["node"] for edge in clusters_data.get("edges", [])]

        # Filter clusters by name (case-insensitive)
        matching_clusters = [
            cluster
            for cluster in clusters
            if cluster.get("name", "").lower() == cluster_name.lower()
        ]

        if not matching_clusters:
            raise Abort(
                f"No cluster found with name '{cluster_name}'.",
                subject="Cluster Not Found",
                log_message=f"Cluster '{cluster_name}' not found",
            )

        # Get the first (and should be only) cluster
        cluster = matching_clusters[0]

        # Fetch client secret from API if clientId is available
        client_id = cluster.get("clientId")
        if client_id:
            try:
                client_secret = await get_cluster_client_secret(ctx, client_id)
                cluster["client_secret"] = client_secret
            except Exception as e:
                logger.warning(
                    f"Failed to retrieve client secret for cluster '{cluster_name}': {e}"
                )
                cluster["client_secret"] = None
        else:
            cluster["client_secret"] = None

        return cluster

    except Abort:
        # Re-raise Abort exceptions as they contain user-friendly messages
        raise
    except (httpx.RequestError, ValueError, KeyError, AttributeError) as e:
        logger.error(f"Unexpected error getting cluster '{cluster_name}': {e}")
        raise Abort(
            f"An unexpected error occurred while getting cluster '{cluster_name}'.",
            subject="Unexpected Error",
            log_message=f"Unexpected error: {e}",
        )
