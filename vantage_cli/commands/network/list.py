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
"""List networks command."""

from typing import Annotated, Optional

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def list_networks(
    ctx: typer.Context,
    region: Annotated[
        Optional[str], typer.Option("--region", "-r", help="Filter by region")
    ] = None,
    status: Annotated[
        Optional[str], typer.Option("--status", "-s", help="Filter by status")
    ] = None,
    limit: Annotated[
        Optional[int], typer.Option("--limit", "-l", help="Maximum number of networks to return")
    ] = 10,
):
    """List all virtual networks."""
    if get_effective_json_output(ctx):
        # JSON output
        networks = [
            {
                "network_id": "network-123",
                "name": "production-vpc",
                "cidr": "10.0.0.0/16",
                "region": "us-west-2",
                "status": "active",
                "subnets_count": 2,
            },
            {
                "network_id": "network-124",
                "name": "development-vpc",
                "cidr": "172.16.0.0/16",
                "region": "us-east-1",
                "status": "creating",
                "subnets_count": 1,
            },
        ]

        # Apply filters
        if region:
            networks = [n for n in networks if n["region"] == region]
        if status:
            networks = [n for n in networks if n["status"] == status]

        print_json(
            data={
                "networks": networks[:limit] if limit else networks,
                "total": len(networks),
                "filters": {"region": region, "status": status, "limit": limit},
            }
        )
    else:
        # Rich console output
        console.print("🌐 Virtual Networks:")
        console.print()

        networks = [
            ("network-123", "production-vpc", "10.0.0.0/16", "us-west-2", "active"),
            ("network-124", "development-vpc", "172.16.0.0/16", "us-east-1", "creating"),
        ]

        for net_id, name, cidr, reg, stat in networks:
            console.print(f"  🏷️  [bold blue]{net_id}[/bold blue] - {name}")
            console.print(
                f"      CIDR: [cyan]{cidr}[/cyan] | Region: [yellow]{reg}[/yellow] | Status: [green]{stat}[/green]"
            )
            console.print()

        console.print(f"📊 Total networks: {len(networks)}")
