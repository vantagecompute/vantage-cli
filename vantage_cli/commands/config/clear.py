# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Clear configuration command for Vantage CLI."""

import typer
from rich import print_json
from rich.console import Console
from rich.panel import Panel

from vantage_cli.config import clear_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
def clear_config(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
):
    """Clear all user tokens and configuration."""
    console = Console()

    json_output = getattr(ctx.obj, "json_output", False)

    if not force:
        # Ask for confirmation
        console.print()
        console.print(
            "⚠️  [bold yellow]Warning[/bold yellow]: This will clear all configuration "
            "files and cached tokens for all profiles."
        )
        console.print()

        confirm = typer.confirm("Are you sure you want to continue?")
        if not confirm:
            if json_output:
                print_json(data={"cleared": False, "message": "Operation cancelled"})
            else:
                console.print("Operation cancelled.")
            return

    # Clear the settings
    clear_settings()

    if json_output:
        print_json(
            data={"cleared": True, "message": "All configuration and tokens cleared successfully"}
        )
    else:
        console.print()
        console.print(
            Panel(
                "✅ All configuration files and cached tokens have been cleared.\n\n"
                "You will need to run [bold]vantage login[/bold] to authenticate again.",
                title="[green]Configuration Cleared[/green]",
                border_style="green",
            )
        )
        console.print()
