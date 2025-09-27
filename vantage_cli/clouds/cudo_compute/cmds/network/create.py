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
"""Create Cudo Compute network command."""

import logging

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings

from .. import attach_cudo_compute_client

logger = logging.getLogger(__name__)


@attach_settings
@attach_persona
@attach_cudo_compute_client
async def create_network(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id", help="Project ID"),
    network_id: str = typer.Argument(..., help="Unique network identifier"),
    data_center_id: str = typer.Option(..., "--data-center-id", help="Data center ID"),
    ip_range: str = typer.Option(
        ..., "--ip-range", help="IP range (CIDR notation, e.g., 10.0.0.0/24)"
    ),
) -> None:
    """Create a new Cudo Compute network."""
    try:
        network = await ctx.obj.cudo_sdk.create_network(
            project_id=project_id,
            network_id=network_id,
            data_center_id=data_center_id,
            ip_range=ip_range,
        )
        logger.debug(f"[bold green]Success:[/bold green] Created network '{network_id}'")
    except Exception as e:
        logger.debug(f"[bold red]Error:[/bold red] Failed to create network: {e}")
        raise typer.Exit(code=1)

    ctx.obj.formatter.render_get(
        data=network,
        resource_name=f"Created Network: {network_id}",
    )
