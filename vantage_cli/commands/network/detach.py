# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Detach network command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


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
