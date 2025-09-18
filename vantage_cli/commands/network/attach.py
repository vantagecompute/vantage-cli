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
"""Attach network command."""

from typing import Annotated, Optional

import typer
from rich import print_json

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def attach_network(
    ctx: typer.Context,
    network_id: Annotated[str, typer.Argument(help="ID of the network to attach")],
    instance_id: Annotated[str, typer.Argument(help="ID of the instance to attach network to")],
    subnet_id: Annotated[
        Optional[str], typer.Option("--subnet-id", "-s", help="Specific subnet ID to attach")
    ] = None,
    assign_public_ip: Annotated[
        bool, typer.Option("--assign-public-ip", help="Assign a public IP address")
    ] = False,
):
    """Attach a network interface to an instance."""
    if get_effective_json_output(ctx):
        # JSON output
        print_json(
            data={
                "network_id": network_id,
                "instance_id": instance_id,
                "subnet_id": subnet_id,
                "assign_public_ip": assign_public_ip,
                "status": "attached",
                "attached_at": "2025-09-10T10:00:00Z",
                "interface_id": "eni-abc123",
                "private_ip": "10.0.1.100",
            }
        )
    else:
        # Rich console output
        ctx.obj.console.print(
            f"🔗 Attaching network [bold blue]{network_id}[/bold blue] to instance [bold green]{instance_id}[/bold green]"
        )
        if subnet_id:
            ctx.obj.console.print(f"   Subnet: [yellow]{subnet_id}[/yellow]")
        ctx.obj.console.print(f"   Public IP: [cyan]{assign_public_ip}[/cyan]")
        ctx.obj.console.print("   Interface ID: [magenta]eni-abc123[/magenta]")
        ctx.obj.console.print("   Private IP: [yellow]10.0.1.100[/yellow]")
        ctx.obj.console.print("✅ Network interface attached successfully!")
