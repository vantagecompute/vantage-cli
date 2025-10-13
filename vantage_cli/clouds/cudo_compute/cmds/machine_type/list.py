# Copyright (C) 2025 Vantage Compute Corporation
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
"""List virtual machine types for Cudo Compute."""

import logging
from typing import Optional

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings

from .. import attach_cudo_compute_client

logger = logging.getLogger(__name__)


@attach_settings
@attach_persona
@attach_cudo_compute_client
async def list_machine_types(
    ctx: typer.Context,
    datacenter_id: Optional[str] = typer.Option(
        None,
        "--datacenter-id",
        help="Filter machine types by data center ID. If not provided, shows all machine types across all data centers.",
    ),
    project_id: Optional[str] = typer.Option(
        None,
        "--project-id",
        help="Project ID for custom pricing (optional)",
    ),
) -> None:
    """List all bare-metal machine types available.

    If --datacenter-id is not provided, returns machine types for all data centers.
    """
    try:
        all_machine_types = await ctx.obj.cudo_sdk.list_machine_types(project_id=project_id)

        if datacenter_id:
            # Filter for specific data center
            machine_types = [mt for mt in all_machine_types if mt.data_center_id == datacenter_id]

            if not machine_types:
                typer.echo(
                    f"No machine types found for data center '{datacenter_id}'",
                    err=True,
                )
                raise typer.Exit(1)

            # Convert Pydantic models to dicts for the formatter
            machine_types_data = [mt.model_dump() for mt in machine_types]

            ctx.obj.formatter.render_list(
                data=machine_types_data,
                resource_name=f"Bare-Metal Machine Types for {datacenter_id}",
            )
        else:
            # Show all machine types
            if not all_machine_types:
                typer.echo("No bare-metal machine types found", err=True)
                raise typer.Exit(1)

            # Convert Pydantic models to dicts for the formatter
            all_machine_types_data = [mt.model_dump() for mt in all_machine_types]

            ctx.obj.formatter.render_list(
                data=all_machine_types_data,
                resource_name="Bare-Metal Machine Types",
            )
    except typer.Exit:
        raise
    except Exception as e:
        logger.debug(f"Failed to list bare-metal machine types: {e}")
        typer.echo(f"Error listing bare-metal machine types: {e}", err=True)
        raise typer.Exit(code=1)
