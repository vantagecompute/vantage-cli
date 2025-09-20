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
"""Update storage command."""

from typing import Annotated, Optional

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import RenderStepOutput


@handle_abort
@attach_settings
async def update_storage(
    ctx: typer.Context,
    storage_id: Annotated[str, typer.Argument(help="ID of the storage volume to update")],
    name: Annotated[
        Optional[str], typer.Option("--name", "-n", help="New name for the storage volume")
    ] = None,
    size: Annotated[
        Optional[int], typer.Option("--size", "-s", help="New size in GB (expansion only)")
    ] = None,
    description: Annotated[
        Optional[str], typer.Option("--description", "-d", help="New description")
    ] = None,
    iops: Annotated[Optional[int], typer.Option("--iops", help="New IOPS setting")] = None,
):
    """Update a storage volume configuration."""
    json_output = getattr(ctx.obj, "json_output", False)
    verbose = getattr(ctx.obj, "verbose", False)

    # Get command start time for timing
    command_start_time = getattr(ctx.obj, "command_start_time", None) if ctx.obj else None

    # Build updates object
    updates = {}
    if name:
        updates["name"] = name
    if size:
        updates["size_gb"] = size
    if description:
        updates["description"] = description
    if iops:
        updates["iops"] = iops

    # Mock update response data
    update_data = {
        "storage_id": storage_id,
        "updates": updates,
        "status": "updated",
        "updated_at": "2025-09-10T10:00:00Z",
    }

    # Create renderer once
    renderer = RenderStepOutput(
        console=ctx.obj.console,
        operation_name=f"Update Storage '{storage_id}'",
        step_names=[]
        if json_output
        else ["Validating updates", "Applying changes", "Formatting output"],
        verbose=verbose,
        command_start_time=command_start_time,
    )

    # Handle JSON output first
    if json_output:
        return renderer.json_bypass(update_data)

    with renderer:
        renderer.complete_step("Validating updates")
        renderer.complete_step("Applying changes")
        renderer.start_step("Formatting output")

        ctx.obj.console.print(f"🔄 Updating storage volume [bold blue]{storage_id}[/bold blue]")

        if name:
            ctx.obj.console.print(f"   Name: [green]{name}[/green]")
        if size:
            ctx.obj.console.print(f"   Size: [yellow]{size} GB[/yellow]")
        if description:
            ctx.obj.console.print(f"   Description: {description}")
        if iops:
            ctx.obj.console.print(f"   IOPS: [cyan]{iops}[/cyan]")

        ctx.obj.console.print("✅ Storage volume updated successfully!")

        renderer.complete_step("Formatting output")
