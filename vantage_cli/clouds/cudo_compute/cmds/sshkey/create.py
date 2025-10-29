# Copyright (c) 2025 Vantage Compute, Inc.
#
# SPDX-License-Identifier: MIT

"""Create Cudo Compute SSH key command."""

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
async def create_ssh_key(
    ctx: Context,
    public_key: str = typer.Option(..., "--public-key", help="SSH public key content"),
) -> None:
    """Create a new SSH key."""
    try:
        ssh_key = await ctx.obj.cudo_sdk.create_ssh_key(public_key)

        typer.echo(f"Successfully created SSH key: {ssh_key.get('id', 'unknown')}")
        ctx.obj.formatter.render_get(
            data=ssh_key,
            resource_name="Created SSH Key",
        )
    except Exception as e:
        logger.debug(f"Failed to create SSH key: {e}")
        typer.echo(f"Error creating SSH key: {e}", err=True)
        raise typer.Exit(code=1)
