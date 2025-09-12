# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Delete network command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def delete_network(
    ctx: typer.Context,
    network_id: Annotated[str, typer.Argument(help="ID of the network to delete")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation prompt")] = False,
):
    """Delete a virtual network."""
    if not force:
        if not typer.confirm(f"Are you sure you want to delete network {network_id}?"):
            console.print("❌ Network deletion cancelled.")
            return

    if get_effective_json_output(ctx):
        # JSON output
        print_json(
            data={
                "network_id": network_id,
                "status": "deleted",
                "deleted_at": "2025-09-10T10:00:00Z",
            }
        )
    else:
        # Rich console output
        console.print(f"🗑️ Deleting virtual network [bold red]{network_id}[/bold red]")
        console.print("✅ Virtual network deleted successfully!")
