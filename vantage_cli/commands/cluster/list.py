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
"""List clusters command."""

import typer
from loguru import logger

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.render import UniversalOutputFormatter
from vantage_cli.sdk.cluster.crud import cluster_sdk


@handle_abort
@attach_settings
async def list_clusters(
    ctx: typer.Context,
):
    """List all Vantage clusters."""
    # Use UniversalOutputFormatter for consistent output
    formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=ctx.obj.json_output)

    try:
        # Use the SDK to get clusters
        logger.debug("Using SDK to list clusters")
        clusters = await cluster_sdk.list_clusters(ctx)

        if not clusters:
            formatter.render_list(
                data=[], resource_name="Clusters", empty_message="No clusters found."
            )
            return

        # Convert Cluster objects to dict format for the formatter
        clusters_data = []
        for cluster in clusters:
            cluster_dict = {
                "name": cluster.name,
                "status": cluster.status,
                "provider": cluster.provider,
                "owner_email": cluster.owner_email,
                "client_id": cluster.client_id,
                "description": cluster.description[:47] + "..."
                if cluster.description and len(cluster.description) > 50
                else cluster.description,
            }
            clusters_data.append(cluster_dict)

        # Use formatter to render the clusters list
        formatter.render_list(
            data=clusters_data, resource_name="Clusters", empty_message="No clusters found."
        )

    except Abort:
        # Re-raise Abort exceptions as they contain user-friendly messages
        raise
    except Exception as e:
        logger.error(f"Unexpected error listing clusters: {e}")
        formatter.render_error(
            error_message="An unexpected error occurred while listing clusters.",
            details={"error": str(e)},
        )
