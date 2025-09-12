# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Get network command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def get_network(
    ctx: typer.Context,
    network_id: Annotated[str, typer.Argument(help="ID of the network to retrieve")],
):
    """Get details of a specific virtual network."""
    if get_effective_json_output(ctx):
        # JSON output
        print_json(
            data={
                "network_id": network_id,
                "name": "production-vpc",
                "cidr": "10.0.0.0/16",
                "region": "us-west-2",
                "status": "active",
                "enable_dns": True,
                "description": "Production VPC for web services",
                "created_at": "2025-09-01T09:00:00Z",
                "updated_at": "2025-09-10T10:00:00Z",
                "subnets": ["subnet-123", "subnet-456"],
                "route_tables": ["rtb-789"],
                "internet_gateway": "igw-abc",
            }
        )
    else:
        # Rich console output
        console.print(f"🌐 Virtual Network: [bold blue]{network_id}[/bold blue]")
        console.print("   Name: [green]production-vpc[/green]")
        console.print("   CIDR: [yellow]10.0.0.0/16[/yellow]")
        console.print("   Region: [cyan]us-west-2[/cyan]")
        console.print("   Status: [green]active[/green]")
        console.print("   DNS Enabled: [magenta]True[/magenta]")
        console.print("   Description: Production VPC for web services")
        console.print("   Subnets: [blue]subnet-123, subnet-456[/blue]")
        console.print("   Internet Gateway: [yellow]igw-abc[/yellow]")
        console.print("   Created: 2025-09-01T09:00:00Z")
        console.print("   Updated: 2025-09-10T10:00:00Z")
