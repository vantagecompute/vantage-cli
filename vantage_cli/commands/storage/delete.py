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
"""Delete storage command."""

from typing import Annotated

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import RenderStepOutput


@handle_abort
@attach_settings
async def delete_storage(
    ctx: typer.Context,
    storage_id: Annotated[str, typer.Argument(help="ID of the storage volume to delete")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation prompt")] = False,
):
    """Delete a storage volume."""
    json_output = getattr(ctx.obj, "json_output", False)
    verbose = getattr(ctx.obj, "verbose", False)

    # Get command start time for timing
    command_start_time = getattr(ctx.obj, "command_start_time", None) if ctx.obj else None

    # Mock delete response data
    delete_data = {
        "storage_id": storage_id,
        "status": "deleted",
        "deleted_at": "2025-09-10T10:00:00Z",
    }

    # Create renderer once
    renderer = RenderStepOutput(
        console=ctx.obj.console,
        operation_name=f"Delete Storage '{storage_id}'",
        step_names=[]
        if json_output
        else ["Confirming deletion", "Deleting storage volume", "Formatting output"],
        verbose=verbose,
        command_start_time=command_start_time,
    )

    # Handle JSON output first
    if json_output:
        # Still need confirmation for JSON mode
        if not force:
            if not typer.confirm(f"Are you sure you want to delete storage volume {storage_id}?"):
                ctx.obj.console.print("❌ Storage deletion cancelled.")
                return
        return renderer.json_bypass(delete_data)

    with renderer:
        renderer.start_step("Confirming deletion")
        if not force:
            if not typer.confirm(f"Are you sure you want to delete storage volume {storage_id}?"):
                ctx.obj.console.print("❌ Storage deletion cancelled.")
                return
        renderer.complete_step("Confirming deletion")

        renderer.complete_step("Deleting storage volume")
        renderer.start_step("Formatting output")

        ctx.obj.console.print(f"🗑️ Deleting storage volume [bold red]{storage_id}[/bold red]")
        ctx.obj.console.print("✅ Storage volume deleted successfully!")

        renderer.complete_step("Formatting output")
