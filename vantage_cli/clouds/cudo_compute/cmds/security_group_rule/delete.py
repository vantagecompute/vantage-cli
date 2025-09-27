# Copyright (c) 2025 Vantage Compute, Inc.
#
# SPDX-License-Identifier: MIT

"""Delete security group rule command."""

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
async def delete_security_group_rule(
    ctx: Context,
    security_group_id: str = typer.Argument(
        ...,
        help="Security group ID",
    ),
    rule_id: str = typer.Argument(
        ...,
        help="Rule ID to delete",
    ),
    project_id: str = typer.Option(
        None,
        "--project-id",
        "-p",
        help="Project ID (uses default if not specified)",
    ),
) -> None:
    """Delete a security group rule."""
    try:
        # Use default project if not specified
        if not project_id:
            project_id = ctx.obj.settings.cudo_compute_project_id

        await ctx.obj.cudo_sdk.delete_security_group_rule(project_id, security_group_id, rule_id)

        typer.echo(f"✓ Security group rule {rule_id} deleted successfully")
    except ValueError as e:
        logger.debug(f"Rule not found: {e}")
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        logger.debug(f"Failed to delete security group rule: {e}")
        typer.echo(f"Error deleting security group rule: {e}", err=True)
        raise typer.Exit(code=1)
