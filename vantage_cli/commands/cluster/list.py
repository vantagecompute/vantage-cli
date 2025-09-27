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

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.sdk.cluster.crud import cluster_sdk


@handle_abort
@attach_settings
async def list_clusters(
    ctx: typer.Context,
):
    """List all Vantage clusters."""
    # Use UniversalOutputFormatter for consistent output

    try:
        # Use the SDK to get clusters
        clusters = await cluster_sdk.list_clusters(ctx)

        if not clusters:
            ctx.obj.formatter.render_list(
                data=[], resource_name="Clusters", empty_message="No clusters found."
            )
            return

        # Convert Cluster objects to dict format for the formatter
        clusters_data = []
        for cluster in clusters:
            # Access Cluster attributes directly
            description = cluster.description
            # Truncate description for list view
            if description and len(description) > 50:
                description = description[:47] + "..."

            cluster_dict = {
                "name": cluster.name,
                "status": cluster.status,
                "provider": cluster.provider,
                "owner_email": cluster.owner_email,
                "client_id": cluster.client_id,
                "description": description,
                "cloud_account_id": cluster.cloud_account_id,
            }
            clusters_data.append(cluster_dict)

        # Use formatter to render the clusters list
        ctx.obj.formatter.render_list(
            data=clusters_data, resource_name="Clusters", empty_message="No clusters found."
        )

    except Abort:
        # Re-raise Abort exceptions as they contain user-friendly messages
        raise
    except Exception as e:
        ctx.obj.formatter.render_error(
            error_message="An unexpected error occurred while listing clusters.",
            details={"error": str(e)},
        )
