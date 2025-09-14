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
"""Create storage command."""

from typing import Annotated, Optional

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort

console = Console()


@handle_abort
@attach_settings
async def create_storage(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the storage volume to create")],
    size: Annotated[
        int, typer.Option("--size", "-s", help="Size of the storage volume in GB")
    ] = 10,
    storage_type: Annotated[
        str, typer.Option("--type", "-t", help="Storage type (ssd, hdd, nvme)")
    ] = "ssd",
    zone: Annotated[
        Optional[str], typer.Option("--zone", "-z", help="Availability zone for the storage")
    ] = None,
    description: Annotated[
        Optional[str],
        typer.Option("--description", "-d", help="Description of the storage volume"),
    ] = None,
):
    """Create a new storage volume."""
    if get_effective_json_output(ctx):
        # JSON output
        print_json(
            data={
                "storage_id": "storage-new-123",
                "name": name,
                "size_gb": size,
                "storage_type": storage_type,
                "zone": zone,
                "description": description,
                "status": "creating",
                "created_at": "2025-09-10T10:00:00Z",
            }
        )
    else:
        # Rich console output
        console.print(f"💾 Creating storage volume [bold blue]{name}[/bold blue]")
        console.print(f"   Size: [green]{size} GB[/green]")
        console.print(f"   Type: [yellow]{storage_type}[/yellow]")
        if zone:
            console.print(f"   Zone: [cyan]{zone}[/cyan]")
        if description:
            console.print(f"   Description: {description}")
        console.print("✅ Storage volume creation initiated!")
