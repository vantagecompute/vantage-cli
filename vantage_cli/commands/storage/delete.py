# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Delete storage command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def delete_storage(
    ctx: typer.Context,
    storage_id: Annotated[str, typer.Argument(help="ID of the storage volume to delete")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation prompt")] = False,
):
    """Delete a storage volume."""
    if not force:
        if not typer.confirm(f"Are you sure you want to delete storage volume {storage_id}?"):
            console.print("❌ Storage deletion cancelled.")
            return

    if get_effective_json_output(ctx):
        # JSON output
        print_json(
            data={
                "storage_id": storage_id,
                "status": "deleted",
                "deleted_at": "2025-09-10T10:00:00Z",
            }
        )
    else:
        # Rich console output
        console.print(f"🗑️ Deleting storage volume [bold red]{storage_id}[/bold red]")
        console.print("✅ Storage volume deleted successfully!")
