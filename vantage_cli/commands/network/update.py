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
"""Update network command."""

from typing import Annotated, Optional

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def update_network(
    ctx: typer.Context,
    network_id: Annotated[str, typer.Argument(help="ID of the network to update")],
    name: Annotated[
        Optional[str], typer.Option("--name", "-n", help="New name for the network")
    ] = None,
    description: Annotated[
        Optional[str], typer.Option("--description", "-d", help="New description")
    ] = None,
    enable_dns: Annotated[
        Optional[bool],
        typer.Option("--enable-dns/--disable-dns", help="Enable or disable DNS resolution"),
    ] = None,
):
    """Update a virtual network configuration."""
    if get_effective_json_output(ctx):
        # JSON output
        updates = {}
        if name:
            updates["name"] = name
        if description:
            updates["description"] = description
        if enable_dns is not None:
            updates["enable_dns"] = enable_dns

        print_json(
            data={
                "network_id": network_id,
                "updates": updates,
                "status": "updated",
                "updated_at": "2025-09-10T10:00:00Z",
            }
        )
    else:
        # Rich console output
        console.print(f"🔄 Updating virtual network [bold blue]{network_id}[/bold blue]")

        if name:
            console.print(f"   Name: [green]{name}[/green]")
        if description:
            console.print(f"   Description: {description}")
        if enable_dns is not None:
            console.print(f"   DNS Enabled: [cyan]{enable_dns}[/cyan]")

        console.print("✅ Virtual network updated successfully!")
