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
"""List Cudo Compute data centers command."""

import logging

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings

from .. import attach_cudo_compute_client

logger = logging.getLogger(__name__)


@attach_settings
@attach_persona
@attach_cudo_compute_client
async def list_data_centers(
    ctx: typer.Context,
) -> None:
    """List all available Cudo Compute data centers."""
    try:
        data_centers = await ctx.obj.cudo_sdk.list_vm_data_centers()
    except Exception as e:
        logger.debug(f"[bold red]Error:[/bold red] Failed to list data centers: {e}")
        raise typer.Exit(code=1)

    if not data_centers:
        logger.debug("No data centers found.")
        return

    # Convert Pydantic models to dicts for the formatter
    data_centers_data = [dc.model_dump() for dc in data_centers]

    ctx.obj.formatter.render_list(
        data=data_centers_data,
        resource_name="Cudo Compute Data Centers",
    )
