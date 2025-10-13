# Copyright (c) 2025 Vantage Compute, Inc.
#
# SPDX-License-Identifier: MIT

"""Get VM data center command."""

import logging

import typer
from typer import Context

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings

from .. import attach_cudo_compute_client

logger = logging.getLogger(__name__)


@attach_settings
@attach_persona
@attach_cudo_compute_client
async def get_vm_data_center(
    ctx: Context,
    data_center_id: str = typer.Argument(
        ...,
        help="Data center ID",
    ),
) -> None:
    """Get details of a specific VM data center."""
    try:
        # List all data centers and filter by ID
        data_centers = await ctx.obj.cudo_sdk.list_vm_data_centers()

        # Find the requested data center
        data_center = next((dc for dc in data_centers if dc.id == data_center_id), None)

        if not data_center:
            typer.echo(f"Error: Data center '{data_center_id}' not found", err=True)
            raise typer.Exit(code=1)

        # Convert Pydantic model to dict for the formatter
        data_center_data = data_center.model_dump()

        ctx.obj.formatter.render_get(
            data=data_center_data,
            resource_name="VM Data Center",
        )
    except typer.Exit:
        raise
    except Exception as e:
        logger.debug(f"Failed to get VM data center: {e}")
        typer.echo(f"Error getting VM data center: {e}", err=True)
        raise typer.Exit(code=1)
