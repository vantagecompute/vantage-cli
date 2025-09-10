# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Get storage command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def get_storage(
    ctx: typer.Context,
    storage_id: Annotated[str, typer.Argument(help="ID of the storage volume to retrieve")],
):
    """Get details of a specific storage volume."""
    if get_effective_json_output(ctx):
        # JSON output
        print_json(
            data={
                "storage_id": storage_id,
                "name": "web-data-volume",
                "size_gb": 100,
                "storage_type": "ssd",
                "zone": "us-west-2a",
                "status": "available",
                "description": "Primary data storage for web application",
                "created_at": "2025-09-01T09:00:00Z",
                "updated_at": "2025-09-10T10:00:00Z",
                "attached_to": "instance-456",
                "mount_point": "/data",
                "iops": 3000,
                "throughput_mbps": 125,
            }
        )
    else:
        # Rich console output
        console.print(f"💾 Storage Volume: [bold blue]{storage_id}[/bold blue]")
        console.print("   Name: [green]web-data-volume[/green]")
        console.print("   Size: [yellow]100 GB[/yellow]")
        console.print("   Type: [cyan]ssd[/cyan]")
        console.print("   Zone: [magenta]us-west-2a[/magenta]")
        console.print("   Status: [green]available[/green]")
        console.print("   Description: Primary data storage for web application")
        console.print("   Attached to: [blue]instance-456[/blue]")
        console.print("   Mount Point: [yellow]/data[/yellow]")
        console.print("   IOPS: [cyan]3000[/cyan]")
        console.print("   Throughput: [magenta]125 MB/s[/magenta]")
        console.print("   Created: 2025-09-01T09:00:00Z")
        console.print("   Updated: 2025-09-10T10:00:00Z")
