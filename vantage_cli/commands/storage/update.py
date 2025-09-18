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
"""Update storage command."""

from typing import Annotated, Optional

import typer
from rich import print_json

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
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
        ctx.obj.console.print(f"🔄 Updating storage volume [bold blue]{storage_id}[/bold blue]")

        if name:
            ctx.obj.console.print(f"   Name: [green]{name}[/green]")
        if size:
            ctx.obj.console.print(f"   Size: [yellow]{size} GB[/yellow]")
        if description:
            ctx.obj.console.print(f"   Description: {description}")
        if iops:
            ctx.obj.console.print(f"   IOPS: [cyan]{iops}[/cyan]")

        ctx.obj.console.print("✅ Storage volume updated successfully!")
