# Copyright (c) 2025 Vantage Compute, Inc.
#
# SPDX-License-Identifier: MIT

"""Get Cudo Compute SSH key command."""

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
async def get_ssh_key(
    ctx: Context,
    ssh_key_id: str = typer.Argument(..., help="SSH key ID"),
) -> None:
    """Get details of a specific SSH key."""
    try:
        ssh_key = await ctx.obj.cudo_sdk.get_ssh_key(ssh_key_id)

        # Convert Pydantic model to dict for the formatter
        ssh_key_data = ssh_key.model_dump() if ssh_key else {}

        ctx.obj.formatter.render_get(
            data=ssh_key_data,
            resource_name=f"SSH Key: {ssh_key_id}",
        )
    except Exception as e:
        logger.debug(f"Failed to get SSH key {ssh_key_id}: {e}")
        typer.echo(f"Error getting SSH key: {e}", err=True)
        raise typer.Exit(code=1)
