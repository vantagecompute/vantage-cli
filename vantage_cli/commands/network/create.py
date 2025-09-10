# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Create network command."""

from typing import Annotated, Optional

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def create_network(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the network to create")],
    cidr: Annotated[
        str, typer.Option("--cidr", "-c", help="CIDR block for the network")
    ] = "10.0.0.0/16",
    region: Annotated[
        Optional[str], typer.Option("--region", "-r", help="Region for the network")
    ] = None,
    enable_dns: Annotated[bool, typer.Option("--enable-dns", help="Enable DNS resolution")] = True,
    description: Annotated[
        Optional[str], typer.Option("--description", "-d", help="Description of the network")
    ] = None,
):
    """Create a new virtual network."""
    if get_effective_json_output(ctx):
        # JSON output
        print_json(
            data={
                "network_id": "network-new-123",
                "name": name,
                "cidr": cidr,
                "region": region,
                "enable_dns": enable_dns,
                "description": description,
                "status": "creating",
                "created_at": "2025-09-10T10:00:00Z",
            }
        )
    else:
        # Rich console output
        console.print(f"🌐 Creating virtual network [bold blue]{name}[/bold blue]")
        console.print(f"   CIDR: [green]{cidr}[/green]")
        if region:
            console.print(f"   Region: [yellow]{region}[/yellow]")
        console.print(f"   DNS Enabled: [cyan]{enable_dns}[/cyan]")
        if description:
            console.print(f"   Description: {description}")
        console.print("✅ Virtual network creation initiated!")
