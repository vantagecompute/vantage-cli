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
"""Get details of a specific VM machine type for Cudo Compute."""

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
async def get_vm_machine_type(
    ctx: typer.Context,
    datacenter_id: str = typer.Argument(
        ...,
        help="Data center ID",
    ),
    machine_type: str = typer.Argument(
        ...,
        help="Machine type identifier (e.g., 'epyc-genoa-a100-pcie', 'sapphire-rapids-h100')",
    ),
    project_id: Optional[str] = typer.Option(
        None,
        "--project-id",
        help="Project ID for custom pricing (optional)",
    ),
) -> None:
    """Get details of a specific VM machine type.

    Retrieves detailed information about a VM machine type including pricing,
    CPU/GPU models, and resource limits for a specific data center.
    """
    try:
        machine_type_details = await ctx.obj.cudo_sdk.get_vm_machine_type(
            data_center_id=datacenter_id,
            machine_type_id=machine_type,
            project_id=project_id,
        )

        # Convert Pydantic model to dict for the formatter
        machine_type_data = machine_type_details.model_dump() if machine_type_details else {}

        ctx.obj.formatter.render_get(
            data=machine_type_data,
            resource_name=f"VM Machine Type: {machine_type}",
        )
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            typer.echo(
                f"VM machine type '{machine_type}' not found in data center '{datacenter_id}'",
                err=True,
            )
        else:
            typer.echo(f"Error: {error_msg}", err=True)
        raise typer.Exit(1)
