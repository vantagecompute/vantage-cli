# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Delete license configuration command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def delete_license_configuration(
    ctx: typer.Context,
    config_id: Annotated[str, typer.Argument(help="ID of the license configuration to delete")],
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Force delete without confirmation")
    ] = False,
):
    """Delete a license configuration."""
    # Confirmation unless force flag is used
    if not force:
        confirmation = typer.confirm(
            f"Are you sure you want to delete license configuration '{config_id}'?"
        )
        if not confirmation:
            console.print("❌ Operation cancelled.")
            raise typer.Exit(0)

    if get_effective_json_output(ctx):
        # JSON output
        print_json(
            data={
                "config_id": config_id,
                "status": "deleted",
                "message": f"License configuration '{config_id}' deleted successfully",
            }
        )
    else:
        # Rich console output
        console.print("⚙️ License Configuration Delete Command")
        console.print(f"📋 Deleting license configuration: {config_id}")
        console.print("⚠️  Not yet implemented - this is a stub")
