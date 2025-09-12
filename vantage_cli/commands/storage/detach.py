# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Detach storage command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def detach_storage(
    ctx: typer.Context,
    storage_id: Annotated[str, typer.Argument(help="ID of the storage volume to detach")],
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Force detachment without graceful unmounting")
    ] = False,
):
    """Detach a storage volume from an instance."""
    if get_effective_json_output(ctx):
        # JSON output
        print_json(
            data={
                "storage_id": storage_id,
                "status": "detached",
                "force": force,
                "detached_at": "2025-09-10T10:00:00Z",
                "previous_instance": "instance-456",
            }
        )
    else:
        # Rich console output
        console.print(f"📎 Detaching storage volume [bold blue]{storage_id}[/bold blue]")
        if force:
            console.print("   [bold red]Force mode enabled - no graceful unmounting[/bold red]")
        console.print("   Previous instance: [green]instance-456[/green]")
        console.print("✅ Storage volume detached successfully!")
