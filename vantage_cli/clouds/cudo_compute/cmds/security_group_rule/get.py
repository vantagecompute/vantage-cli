# Copyright (c) 2025 Vantage Compute, Inc.
#
# SPDX-License-Identifier: MIT

"""Get security group rule command."""

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
async def get_security_group_rule(
    ctx: Context,
    security_group_id: str = typer.Argument(
        ...,
        help="Security group ID",
    ),
    rule_id: str = typer.Argument(
        ...,
        help="Rule ID",
    ),
    project_id: str = typer.Option(
        None,
        "--project-id",
        "-p",
        help="Project ID (uses default if not specified)",
    ),
) -> None:
    """Get details of a specific security group rule."""
    try:
        # Use default project if not specified
        if not project_id:
            project_id = ctx.obj.settings.cudo_compute_project_id

        rule = await ctx.obj.cudo_sdk.get_security_group_rule(
            project_id, security_group_id, rule_id
        )

        # Convert Pydantic model to dict for the formatter
        rule_data = rule.model_dump() if rule else {}

        ctx.obj.formatter.render_get(
            data=rule_data,
            resource_name="Security Group Rule",
        )
    except ValueError as e:
        logger.debug(f"Rule not found: {e}")
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        logger.debug(f"Failed to get security group rule: {e}")
        typer.echo(f"Error getting security group rule: {e}", err=True)
        raise typer.Exit(code=1)
