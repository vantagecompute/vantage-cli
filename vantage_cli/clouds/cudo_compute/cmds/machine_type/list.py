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

from typing import Optional

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings
from vantage_cli.render import RenderStepOutput

from .. import attach_cudo_compute_client


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
    formatter: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table, json, yaml",
    ),
) -> None:
    """List all data centers available for virtual machines.
    
    If --datacenter-id is not provided, iterates over all data centers
    and returns machine types for each.
    """
    sdk = ctx.obj["cudo_compute_sdk"]
    
    with RenderStepOutput.json_bypass(formatter):
        if datacenter_id:
            # Filter for specific data center
            all_machine_types = await sdk.list_vm_machine_types(project_id=project_id)
            machine_types = [
                mt for mt in all_machine_types 
                if mt.get("dataCenterId") == datacenter_id
            ]
            
            if not machine_types:
                typer.echo(
                    f"No machine types found for data center '{datacenter_id}'",
                    err=True,
                )
                raise typer.Exit(1)
            
            RenderStepOutput.render_output(
                machine_types,
                formatter=formatter,
                title=f"Machine Types for {datacenter_id}",
            )
        else:
            # Get all machine types across all data centers
            machine_types = await sdk.list_vm_machine_types(project_id=project_id)
            
            if not machine_types:
                typer.echo("No machine types found", err=True)
                raise typer.Exit(1)
            
            RenderStepOutput.render_output(
                machine_types,
                formatter=formatter,
                title="VM Machine Types",
            )
