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

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.commands.cluster.utils import get_cluster_by_name
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort

from .render import render_cluster_details


@attach_settings
async def get_cluster(
    ctx: typer.Context,
    cluster_name: Annotated[str, typer.Argument(help="Name of the cluster to get details for")],
):
    """Get details of a specific Vantage cluster."""
    cluster = await get_cluster_by_name(ctx=ctx, cluster_name=cluster_name)
    if not cluster:
        raise Abort(
            f"No cluster found with name '{cluster_name}'.",
            subject="Cluster Not Found",
            log_message=f"Cluster '{cluster_name}' not found",
        )

    # Get JSON flag from context (automatically set by AsyncTyper)
    json_output = getattr(ctx.obj, "json_output", False) if ctx.obj else False
    render_cluster_details(cluster, json_output=get_effective_json_output(ctx, json_output))
