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
"""List storage command."""

from typing import Annotated, Optional

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def list_storage(
    ctx: typer.Context,
    zone: Annotated[
        Optional[str], typer.Option("--zone", "-z", help="Filter by availability zone")
    ] = None,
    storage_type: Annotated[
        Optional[str], typer.Option("--type", "-t", help="Filter by storage type")
    ] = None,
    status: Annotated[
        Optional[str], typer.Option("--status", "-s", help="Filter by status")
    ] = None,
    limit: Annotated[
        Optional[int],
        typer.Option("--limit", "-l", help="Maximum number of storage volumes to return"),
    ] = 10,
):
    """List all storage volumes."""
    if get_effective_json_output(ctx):
        # JSON output
        volumes = [
            {
                "storage_id": "storage-123",
                "name": "web-data-volume",
                "size_gb": 100,
                "storage_type": "ssd",
                "zone": "us-west-2a",
                "status": "available",
                "attached_to": "instance-456",
            },
            {
                "storage_id": "storage-124",
                "name": "backup-volume",
                "size_gb": 500,
                "storage_type": "hdd",
                "zone": "us-west-2b",
                "status": "creating",
                "attached_to": None,
            },
        ]

        # Apply filters
        if zone:
            volumes = [v for v in volumes if v["zone"] == zone]
        if storage_type:
            volumes = [v for v in volumes if v["storage_type"] == storage_type]
        if status:
            volumes = [v for v in volumes if v["status"] == status]

        print_json(
            data={
                "volumes": volumes[:limit] if limit else volumes,
                "total": len(volumes),
                "filters": {
                    "zone": zone,
                    "storage_type": storage_type,
                    "status": status,
                    "limit": limit,
                },
            }
        )
    else:
        # Rich console output
        console.print("💾 Storage Volumes:")
        console.print()

        volumes = [
            ("storage-123", "web-data-volume", "100 GB", "ssd", "available", "instance-456"),
            ("storage-124", "backup-volume", "500 GB", "hdd", "creating", "unattached"),
        ]

        for vol_id, name, size, stype, stat, attached in volumes:
            console.print(f"  🏷️  [bold blue]{vol_id}[/bold blue] - {name}")
            console.print(
                f"      Size: [cyan]{size}[/cyan] | Type: [yellow]{stype}[/yellow] | Status: [green]{stat}[/green] | Attached: [magenta]{attached}[/magenta]"
            )
            console.print()

        console.print(f"📊 Total volumes: {len(volumes)}")
