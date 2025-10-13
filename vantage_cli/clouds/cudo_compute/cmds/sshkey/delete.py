# Copyright (c) 2025 Vantage Compute, Inc.
#
# SPDX-License-Identifier: MIT

"""Delete Cudo Compute SSH key command."""

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
async def delete_ssh_key(
    ctx: Context,
    ssh_key_id: str = typer.Argument(..., help="SSH key ID"),
) -> None:
    """Delete an SSH key."""
    try:
        await ctx.obj.cudo_sdk.delete_ssh_key(ssh_key_id)

        typer.echo(f"Successfully deleted SSH key: {ssh_key_id}")
    except Exception as e:
        logger.debug(f"Failed to delete SSH key {ssh_key_id}: {e}")
        typer.echo(f"Error deleting SSH key: {e}", err=True)
        raise typer.Exit(code=1)
