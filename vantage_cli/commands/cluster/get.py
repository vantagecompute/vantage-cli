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

from vantage_cli.commands.cluster.utils import get_cluster_by_name
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.render import RenderStepOutput

from .render import render_cluster_details


@handle_abort
@attach_settings
async def get_cluster(
    ctx: typer.Context,
    cluster_name: Annotated[str, typer.Argument(help="Name of the cluster to get details for")],
):
    """Get details of a specific Vantage cluster."""
    verbose = getattr(ctx.obj, "verbose", False)
    json_output = getattr(ctx.obj, "json_output", False)
    command_start_time = getattr(ctx.obj, "command_start_time", None) if ctx.obj else None

    renderer = RenderStepOutput(
        console=ctx.obj.console,
        operation_name=f"Getting cluster '{cluster_name}'",
        step_names=[
            "Fetching cluster details",
            "Complete",
        ],
        verbose=verbose,
        command_start_time=command_start_time,
    )

    cluster = await get_cluster_by_name(ctx=ctx, cluster_name=cluster_name)
    if not cluster:
        raise Abort(
            f"No cluster found with name '{cluster_name}'.",
            subject="Cluster Not Found",
            log_message=f"Cluster '{cluster_name}' not found",
        )

    # Handle JSON output first
    if json_output:
        renderer.json_bypass(cluster)
        return

    with renderer:
        renderer.start_step("Fetching cluster details")
        renderer.table_step(render_cluster_details(cluster))
        renderer.complete_step("Complete")
