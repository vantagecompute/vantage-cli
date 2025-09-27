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
"""Get Cudo Compute data center command."""

import logging

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings

from .. import attach_cudo_compute_client

logger = logging.getLogger(__name__)


@attach_settings
@attach_persona
@attach_cudo_compute_client
async def get_data_center(
    ctx: typer.Context,
    data_center_id: str = typer.Argument(..., help="Data center ID"),
) -> None:
    """Get details of a specific Cudo Compute data center."""
    try:
        data_center = await ctx.obj.cudo_sdk.get_data_center(data_center_id=data_center_id)
    except Exception as e:
        logger.debug(f"[bold red]Error:[/bold red] Failed to get data center: {e}")
        raise typer.Exit(code=1)

    if not data_center:
        logger.debug(f"Data center '{data_center_id}' not found.")
        raise typer.Exit(code=1)

    # Convert Pydantic model to dict for the formatter
    data_center_data = data_center.model_dump()

    ctx.obj.formatter.render_get(
        data=data_center_data,
        resource_name=f"Data Center: {data_center_id}",
    )
