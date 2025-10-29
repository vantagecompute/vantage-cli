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
"""Get cluster command for Vantage CLI."""

import typer
from typing_extensions import Annotated

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.sdk.cluster.crud import cluster_sdk


@handle_abort
@attach_settings
async def get_cluster(
    ctx: typer.Context,
    cluster_name: Annotated[str, typer.Argument(help="Name of the cluster to get details for")],
):
    """Get details of a specific Vantage cluster."""
    # Use UniversalOutputFormatter for consistent output

    try:
        # Use SDK to get cluster
        cluster = await cluster_sdk.get_cluster(ctx, cluster_name)

        if not cluster:
            ctx.obj.formatter.render_error(
                error_message=f"No cluster found with name '{cluster_name}'."
            )
            raise Abort(
                f"No cluster found with name '{cluster_name}'.",
                subject="Cluster Not Found",
                log_message=f"Cluster '{cluster_name}' not found",
            )

        # Access Cluster attributes directly to build data dict
        cluster_data = {
            "name": cluster.name,
            "status": cluster.status,
            "client_id": cluster.client_id,
            "client_secret": cluster.client_secret,
            "description": cluster.description,
            "owner_email": cluster.owner_email,
            "provider": cluster.provider,
            "cloud_account_id": cluster.cloud_account_id,
            "creation_parameters": cluster.creation_parameters,
            "cluster_type": cluster.cluster_type,
            "is_ready": cluster.is_ready,
            "jupyterhub_url": cluster.jupyterhub_url,
            "jupyterhub_token": cluster.jupyterhub_token,
            "sssd_binder_password": cluster.sssd_binder_password,
        }

        # Use formatter to render the cluster details
        ctx.obj.formatter.render_get(
            data=cluster_data, resource_name="Cluster", resource_id=cluster_name
        )

    except Abort:
        raise
    except Exception as e:
        ctx.obj.formatter.render_error(
            error_message=f"An unexpected error occurred while getting cluster '{cluster_name}'.",
            details={"error": str(e)},
        )
