# Copyright (c) 2025 Vantage Compute, Inc.
#
# SPDX-License-Identifier: MIT

"""Create security group rule command."""

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
async def create_security_group_rule(
    ctx: Context,
    security_group_id: str = typer.Argument(
        ...,
        help="Security group ID",
    ),
    protocol: str = typer.Option(
        ...,
        "--protocol",
        help="Protocol (PROTOCOL_TCP, PROTOCOL_UDP, PROTOCOL_ICMP, PROTOCOL_ALL, etc.)",
    ),
    rule_type: str = typer.Option(
        ...,
        "--rule-type",
        help="Rule type (RULE_TYPE_INBOUND, RULE_TYPE_OUTBOUND)",
    ),
    ip_range_cidr: str = typer.Option(
        ...,
        "--ip-range",
        help="IP range in CIDR format (e.g., 0.0.0.0/0, 192.168.1.0/24)",
    ),
    ports: Optional[str] = typer.Option(
        None,
        "--ports",
        help="Port range (e.g., '80', '80-443')",
    ),
    icmp_type: Optional[str] = typer.Option(
        None,
        "--icmp-type",
        help="ICMP type (for ICMP protocol)",
    ),
    project_id: str = typer.Option(
        None,
        "--project-id",
        "-p",
        help="Project ID (uses default if not specified)",
    ),
) -> None:
    """Create a new security group rule."""
    try:
        # Use default project if not specified
        if not project_id:
            project_id = ctx.obj.settings.cudo_compute_project_id

        result = await ctx.obj.cudo_sdk.create_security_group_rule(
            project_id=project_id,
            security_group_id=security_group_id,
            protocol=protocol,
            rule_type=rule_type,
            ip_range_cidr=ip_range_cidr,
            ports=ports,
            icmp_type=icmp_type,
        )

        typer.echo("✓ Security group rule created successfully")

        # Show the updated security group
        ctx.obj.formatter.render_get(
            data=result,
            resource_name="Security Group",
        )
    except Exception as e:
        logger.debug(f"Failed to create security group rule: {e}")
        typer.echo(f"Error creating security group rule: {e}", err=True)
        raise typer.Exit(code=1)
