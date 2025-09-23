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
"""Clear configuration command for Vantage CLI."""

import typer
from rich.panel import Panel

from vantage_cli.config import clear_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import RenderStepOutput


@handle_abort
async def clear_config(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
):
    """Clear all user tokens and configuration."""
    json_output = getattr(ctx.obj, "json_output", False)
    command_start_time = getattr(ctx.obj, "command_start_time", None) if ctx.obj else None

    renderer = RenderStepOutput(
        console=ctx.obj.console,
        operation_name="Clear Configuration",
        step_names=[] if json_output else ["Validating parameters", "Clearing configuration"],
        verbose=not json_output,
        command_start_time=command_start_time,
    )

    if json_output:
        # Handle confirmation for JSON output
        if not force:
            confirm = typer.confirm("Are you sure you want to continue?")
            if not confirm:
                return renderer.json_bypass({"cleared": False, "message": "Operation cancelled"})

        # Clear the settings
        clear_settings()

        return renderer.json_bypass(
            {"cleared": True, "message": "All configuration and tokens cleared successfully"}
        )

    with renderer:
        # Ask for confirmation if not forced
        if not force:
            # Ask for confirmation
            ctx.obj.console.print()
            ctx.obj.console.print(
                "⚠️  [bold yellow]Warning[/bold yellow]: This will clear all configuration "
                "files and cached tokens for all profiles."
            )
            ctx.obj.console.print()

            confirm = typer.confirm("Are you sure you want to continue?")
            if not confirm:
                ctx.obj.console.print("Operation cancelled.")
                return

        renderer.complete_step("Validating parameters")

        # Clear the settings
        clear_settings()

        renderer.complete_step("Clearing configuration")

        ctx.obj.console.print()
        ctx.obj.console.print(
            Panel(
                "✅ All configuration files and cached tokens have been cleared.\n\n"
                "You will need to run [bold]vantage login[/bold] to authenticate again.",
                title="[green]Configuration Cleared[/green]",
                border_style="green",
            )
        )
        ctx.obj.console.print()
