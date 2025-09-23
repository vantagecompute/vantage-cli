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
"""Delete federation command."""

import typer
from typing_extensions import Annotated

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import RenderStepOutput


@handle_abort
@attach_settings
async def delete_federation(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the federation to delete")],
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Force deletion without confirmation")
    ] = False,
):
    """Delete a Vantage federation."""
    json_output = getattr(ctx.obj, "json_output", False)
    verbose = getattr(ctx.obj, "verbose", False)

    # Get command start time for timing
    command_start_time = getattr(ctx.obj, "command_start_time", None) if ctx.obj else None

    if not force and not json_output:
        # Ask for confirmation
        ctx.obj.console.print(f"⚠️  You are about to delete federation '[red]{name}[/red]'")
        ctx.obj.console.print("This action cannot be undone!")

        confirm = typer.confirm("Are you sure you want to proceed?")
        if not confirm:
            ctx.obj.console.print("Deletion cancelled.")
            return

    # TODO: Implement actual federation deletion logic
    deletion_data = {
        "name": name,
        "force": force,
        "status": "deleted",
        "message": "Federation delete command not yet implemented",
    }

    # Create renderer once
    renderer = RenderStepOutput(
        console=ctx.obj.console,
        operation_name=f"Delete Federation '{name}'",
        step_names=[]
        if json_output
        else ["Validating federation", "Deleting federation", "Formatting output"],
        verbose=verbose,
        command_start_time=command_start_time,
    )

    # Handle JSON output first
    if json_output:
        return renderer.json_bypass(deletion_data)

    with renderer:
        renderer.complete_step("Validating federation")
        renderer.complete_step("Deleting federation")
        renderer.start_step("Formatting output")

        ctx.obj.console.print("🔗 [bold blue]Federation Delete Command[/bold blue]")
        ctx.obj.console.print(f"🗑️  Deleting federation: [bold]{name}[/bold]")
        if force:
            ctx.obj.console.print("💪 Force deletion enabled")
        ctx.obj.console.print("⚠️  [yellow]Not yet implemented - this is a stub[/yellow]")

        renderer.complete_step("Formatting output")
