# Copyright (c) 2025 Vantage Compute, Inc.
#
# SPDX-License-Identifier: MIT

"""List security group rules command."""

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
async def list_security_group_rules(
    ctx: Context,
    security_group_id: str = typer.Argument(
        ...,
        help="Security group ID",
    ),
    project_id: str = typer.Option(
        None,
        "--project-id",
        "-p",
        help="Project ID (uses default if not specified)",
    ),
) -> None:
    """List all rules in a security group."""
    try:
        # Use default project if not specified
        if not project_id:
            project_id = ctx.obj.settings.cudo_compute_project_id

        rules = await ctx.obj.cudo_sdk.list_security_group_rules(project_id, security_group_id)

        # Convert Pydantic models to dicts for the formatter
        rules_data = [r.model_dump() for r in rules]

        ctx.obj.formatter.render_list(
            data=rules_data,
            resource_name="Security Group Rules",
        )
    except Exception as e:
        logger.debug(f"Failed to list security group rules: {e}")
        typer.echo(f"Error listing security group rules: {e}", err=True)
        raise typer.Exit(code=1)
