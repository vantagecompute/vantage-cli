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
"""Get storage command."""

from typing import Annotated

import typer
from rich import print_json

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
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
        ctx.obj.console.print(f"💾 Storage Volume: [bold blue]{storage_id}[/bold blue]")
        ctx.obj.console.print("   Name: [green]web-data-volume[/green]")
        ctx.obj.console.print("   Size: [yellow]100 GB[/yellow]")
        ctx.obj.console.print("   Type: [cyan]ssd[/cyan]")
        ctx.obj.console.print("   Zone: [magenta]us-west-2a[/magenta]")
        ctx.obj.console.print("   Status: [green]available[/green]")
        ctx.obj.console.print("   Description: Primary data storage for web application")
        ctx.obj.console.print("   Attached to: [blue]instance-456[/blue]")
        ctx.obj.console.print("   Mount Point: [yellow]/data[/yellow]")
        ctx.obj.console.print("   IOPS: [cyan]3000[/cyan]")
        ctx.obj.console.print("   Throughput: [magenta]125 MB/s[/magenta]")
        ctx.obj.console.print("   Created: 2025-09-01T09:00:00Z")
        ctx.obj.console.print("   Updated: 2025-09-10T10:00:00Z")
