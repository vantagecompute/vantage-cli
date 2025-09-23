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
"""Create storage command."""

from typing import Annotated, Optional

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import RenderStepOutput


@handle_abort
@attach_settings
async def create_storage(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the storage volume to create")],
    size: Annotated[
        int, typer.Option("--size", "-s", help="Size of the storage volume in GB")
    ] = 10,
    storage_type: Annotated[
        str, typer.Option("--type", "-t", help="Storage type (ssd, hdd, nvme)")
    ] = "ssd",
    zone: Annotated[
        Optional[str], typer.Option("--zone", "-z", help="Availability zone for the storage")
    ] = None,
    description: Annotated[
        Optional[str],
        typer.Option("--description", "-d", help="Description of the storage volume"),
    ] = None,
):
    """Create a new storage volume."""
    json_output = getattr(ctx.obj, "json_output", False)
    verbose = getattr(ctx.obj, "verbose", False)

    # Get command start time for timing
    command_start_time = getattr(ctx.obj, "command_start_time", None) if ctx.obj else None

    # Mock storage creation data
    storage_data = {
        "storage_id": "storage-new-123",
        "name": name,
        "size_gb": size,
        "storage_type": storage_type,
        "zone": zone,
        "description": description,
        "status": "creating",
        "created_at": "2025-09-10T10:00:00Z",
    }

    # Create renderer once
    renderer = RenderStepOutput(
        console=ctx.obj.console,
        operation_name=f"Create Storage '{name}'",
        step_names=[]
        if json_output
        else ["Validating parameters", "Creating storage volume", "Formatting output"],
        verbose=verbose,
        command_start_time=command_start_time,
    )

    # Handle JSON output first
    if json_output:
        return renderer.json_bypass(storage_data)

    with renderer:
        renderer.complete_step("Validating parameters")
        renderer.complete_step("Creating storage volume")
        renderer.start_step("Formatting output")

        ctx.obj.console.print(f"💾 Creating storage volume [bold blue]{name}[/bold blue]")
        ctx.obj.console.print(f"   Size: [green]{size} GB[/green]")
        ctx.obj.console.print(f"   Type: [yellow]{storage_type}[/yellow]")
        if zone:
            ctx.obj.console.print(f"   Zone: [cyan]{zone}[/cyan]")
        if description:
            ctx.obj.console.print(f"   Description: {description}")
        ctx.obj.console.print("✅ Storage volume creation initiated!")

        renderer.complete_step("Formatting output")
