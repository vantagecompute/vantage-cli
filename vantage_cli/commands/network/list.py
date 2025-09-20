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

from typing import Annotated, Any, Dict, List, Optional

import typer
from rich.table import Table

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import RenderStepOutput


@handle_abort
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
    # Get command timing
    command_start_time = getattr(ctx.obj, "command_start_time", None)

    # Check for JSON output mode
    json_output = getattr(ctx.obj, "json_output", False)

    # Mock network data
    networks: List[Dict[str, Any]] = [
        {
            "id": "net-123",
            "name": "production-vpc",
            "region": "us-west-2",
            "status": "active",
            "cidr": "10.0.0.0/16",
            "created_at": "2025-01-01T12:00:00Z",
        },
        {
            "id": "net-456",
            "name": "staging-vpc",
            "region": "us-east-1",
            "status": "active",
            "cidr": "10.1.0.0/16",
            "created_at": "2025-01-02T12:00:00Z",
        },
        {
            "id": "net-789",
            "name": "dev-vpc",
            "region": "us-west-2",
            "status": "pending",
            "cidr": "10.2.0.0/16",
            "created_at": "2025-01-03T12:00:00Z",
        },
    ]

    # Apply filters
    if region:
        networks = [n for n in networks if n["region"] == region]
    if status:
        networks = [n for n in networks if n["status"] == status]
    if limit:
        networks = networks[:limit]

    # If JSON mode, bypass all visual rendering
    if json_output:
        result = {"networks": networks, "count": len(networks)}
        RenderStepOutput.json_bypass(result)
        return

    # Regular rendering for non-JSON mode
    step_names = ["Fetching networks", "Applying filters"]
    console = ctx.obj.console

    with RenderStepOutput(
        console=console,
        operation_name="Listing networks",
        step_names=step_names,
        json_output=json_output,
        command_start_time=command_start_time,
    ) as renderer:
        renderer.advance("Fetching networks", "starting")
        # Simulate fetch
        renderer.advance("Fetching networks", "completed")

        renderer.advance("Applying filters", "starting")
        # Simulate filtering
        renderer.advance("Applying filters", "completed")

        # Create and display table
        table = Table(title="Virtual Networks")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="magenta")
        table.add_column("Region", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("CIDR", style="blue")
        table.add_column("Created", style="dim")

        for network in networks:
            table.add_row(
                network["id"],
                network["name"],
                network["region"],
                network["status"],
                network["cidr"],
                network["created_at"],
            )

        renderer.table_step(table)
