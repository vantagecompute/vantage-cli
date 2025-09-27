# Copyright (c) 2025 Vantage Compute, Inc.
#
# SPDX-License-Identifier: MIT

"""List VM data centers command."""

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
async def list_vm_data_centers(
    ctx: Context,
) -> None:
    """List all data centers available for virtual machines."""
    try:
        data_centers = await ctx.obj.cudo_sdk.list_vm_data_centers()

        # Convert Pydantic models to dicts for the formatter
        data_centers_data = [dc.model_dump() for dc in data_centers]

        ctx.obj.formatter.render_list(
            data=data_centers_data,
            resource_name="VM Data Centers",
        )
    except Exception as e:
        logger.debug(f"Failed to list VM data centers: {e}")
        typer.echo(f"Error listing VM data centers: {e}", err=True)
        raise typer.Exit(code=1)
