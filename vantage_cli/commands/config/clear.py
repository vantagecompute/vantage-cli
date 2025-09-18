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
from rich import print_json
from rich.panel import Panel

from vantage_cli.config import clear_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
def clear_config(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
):
    """Clear all user tokens and configuration."""
    json_output = getattr(ctx.obj, "json_output", False)

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
            if json_output:
                print_json(data={"cleared": False, "message": "Operation cancelled"})
            else:
                ctx.obj.console.print("Operation cancelled.")
            return

    # Clear the settings
    clear_settings()

    if json_output:
        print_json(
            data={"cleared": True, "message": "All configuration and tokens cleared successfully"}
        )
    else:
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
