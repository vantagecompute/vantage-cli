# Copyright (c) 2025 Vantage Compute, Inc.
#
# SPDX-License-Identifier: MIT

"""List Cudo Compute SSH keys command."""

import logging
from typing import Optional

import typer
from typer import Context

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings

from .. import attach_cudo_compute_client

logger = logging.getLogger(__name__)


@attach_settings
@attach_persona
@attach_cudo_compute_client
async def list_ssh_keys(
    ctx: Context,
    page_number: Optional[int] = typer.Option(None, help="Page number for pagination"),
    page_size: Optional[int] = typer.Option(None, help="Number of results per page"),
) -> None:
    """List SSH keys for the current user."""
    try:
        ssh_keys = await ctx.obj.cudo_sdk.list_ssh_keys(
            page_number=page_number,
            page_size=page_size,
        )

        # Convert Pydantic models to dicts for the formatter
        ssh_keys_data = [key.model_dump() for key in ssh_keys]

        ctx.obj.formatter.render_list(
            data=ssh_keys_data,
            resource_name="SSH Keys",
        )
    except Exception as e:
        logger.debug(f"Failed to list SSH keys: {e}")
        typer.echo(f"Error listing SSH keys: {e}", err=True)
        raise typer.Exit(code=1)
