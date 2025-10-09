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

from typing import Optional

import httpx
import typer

from vantage_cli.apps.utils import get_available_apps
from vantage_cli.auth import extract_persona
from vantage_cli.config import Settings
from vantage_cli.exceptions import Abort
from vantage_cli.sdk.cluster.crud import cluster_sdk
from vantage_cli.sdk.cluster.schema import Cluster


def get_cloud_choices() -> list[str]:
    """Get the list of supported clouds from settings."""
    settings = Settings()
    return settings.supported_clouds


def get_app_choices() -> list[str]:
    """Get the list of available deployment apps."""
    try:
        apps = get_available_apps()
        choices = list(apps.keys())
        return choices
    except Exception:
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
        api_url = f"{ctx.obj.settings.get_apis_url()}/admin/management/clients"

        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

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


async def get_cluster_by_name(ctx: typer.Context, cluster_name: str) -> Cluster | None:
    """Get cluster details by name using the cluster SDK.

    Args:
        ctx: Typer context carrying settings/profile
        cluster_name: The name of the cluster to retrieve

    Returns:
        The Cluster object if found, None otherwise
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
        cluster_obj = await cluster_sdk.get_cluster(ctx, cluster_name)

        if not cluster_obj:
            return None

        # Fetch client secret from API if clientId is available and update the cluster object
        client_id = cluster_obj.client_id
        if client_id:
            try:
                client_secret = await get_cluster_client_secret(ctx, client_id)
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
