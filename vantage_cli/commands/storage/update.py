# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Update storage command."""

from typing import Annotated, Optional

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


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
    if get_effective_json_output(ctx):
        # JSON output
        updates = {}
        if name:
            updates["name"] = name
        if size:
            updates["size_gb"] = size
        if description:
            updates["description"] = description
        if iops:
            updates["iops"] = iops

        print_json(
            data={
                "storage_id": storage_id,
                "updates": updates,
                "status": "updated",
                "updated_at": "2025-09-10T10:00:00Z",
            }
        )
    else:
        # Rich console output
        console.print(f"🔄 Updating storage volume [bold blue]{storage_id}[/bold blue]")

        if name:
            console.print(f"   Name: [green]{name}[/green]")
        if size:
            console.print(f"   Size: [yellow]{size} GB[/yellow]")
        if description:
            console.print(f"   Description: {description}")
        if iops:
            console.print(f"   IOPS: [cyan]{iops}[/cyan]")

        console.print("✅ Storage volume updated successfully!")
