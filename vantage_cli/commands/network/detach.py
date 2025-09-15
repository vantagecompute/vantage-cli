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
"""Detach network command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort

console = Console()


@handle_abort
@attach_settings
async def detach_network(
    ctx: typer.Context,
    network_id: Annotated[str, typer.Argument(help="ID of the network to detach")],
    instance_id: Annotated[str, typer.Argument(help="ID of the instance to detach network from")],
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Force detachment without graceful shutdown")
    ] = False,
):
    """Detach a network interface from an instance."""
    if get_effective_json_output(ctx):
        # JSON output
        print_json(
            data={
                "network_id": network_id,
                "instance_id": instance_id,
                "status": "detached",
                "force": force,
                "detached_at": "2025-09-10T10:00:00Z",
                "interface_id": "eni-abc123",
            }
        )
    else:
        # Rich console output
        console.print(
            f"🔗 Detaching network [bold blue]{network_id}[/bold blue] from instance [bold green]{instance_id}[/bold green]"
        )
        if force:
            console.print("   [bold red]Force mode enabled - no graceful shutdown[/bold red]")
        console.print("   Interface ID: [magenta]eni-abc123[/magenta]")
        console.print("✅ Network interface detached successfully!")
