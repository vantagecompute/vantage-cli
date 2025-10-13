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
"""List available applications and active deployments."""

from typing import Optional

import typer
from typing_extensions import Annotated

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.sdk.deployment import deployment_sdk


@attach_settings
@handle_abort
async def list_deployments(
    ctx: typer.Context,
    cloud: Annotated[
        Optional[str],
        typer.Option(
            "--cloud", help="Filter deployments by cloud type (e.g., localhost, aws, gcp)"
        ),
    ] = None,
    status: Annotated[
        Optional[str],
        typer.Option("--status", help="Filter deployments by status (e.g., active, inactive)"),
    ] = None,
) -> None:
    """List all active deployments from ~/.vantage-cli/deployments.yaml."""
    try:
        # Use the SDK to get deployments
        deployments = [
            d.model_dump(mode="json")
            for d in await deployment_sdk.list(ctx, cloud=cloud, status=status)
        ]

        ctx.obj.formatter.render_list(
            data=deployments,
            resource_name="Deployments",
            empty_message="No active deployments found. Use 'vantage app deployment create <app> <cluster>' to create one.",
        )

    except Exception as e:
        raise Abort(
            f"Failed to list deployments: {e}",
            subject="List Deployments Error",
            log_message=f"Deployment list error: {e}",
        )
