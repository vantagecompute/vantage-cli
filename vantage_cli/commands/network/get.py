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
"""Get network command."""

from typing import Annotated, Any, Dict

import typer
from rich.panel import Panel

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import RenderStepOutput


@handle_abort
@attach_settings
async def get_network(
    ctx: typer.Context,
    network_id: Annotated[str, typer.Argument(help="ID of the network to retrieve")],
):
    """Get details of a specific virtual network."""
    # Get command timing
    command_start_time = getattr(ctx.obj, "command_start_time", None)

    # Check for JSON output mode
    json_output = getattr(ctx.obj, "json_output", False)

    # Mock network data
    network: Dict[str, Any] = {
        "id": network_id,
        "name": f"network-{network_id}",
        "region": "us-west-2",
        "status": "active",
        "cidr": "10.0.0.0/16",
        "dns_servers": ["8.8.8.8", "8.8.4.4"],
        "subnets": [
            {"id": "subnet-123", "cidr": "10.0.1.0/24", "availability_zone": "us-west-2a"},
            {"id": "subnet-456", "cidr": "10.0.2.0/24", "availability_zone": "us-west-2b"},
        ],
        "created_at": "2025-01-01T12:00:00Z",
        "updated_at": "2025-01-15T10:30:00Z",
    }

    # If JSON mode, bypass all visual rendering
    if json_output:
        RenderStepOutput.json_bypass(network)
        return

    # Regular rendering for non-JSON mode
    step_names = ["Fetching network details", "Loading subnets"]

    with RenderStepOutput(
        console=ctx.obj.console,
        operation_name="Getting network details",
        step_names=step_names,
        json_output=json_output,
        command_start_time=command_start_time,
    ) as renderer:
        renderer.advance("Fetching network details", "starting")
        # Simulate fetch
        renderer.advance("Fetching network details", "completed")

        renderer.advance("Loading subnets", "starting")
        # Simulate subnet loading
        renderer.advance("Loading subnets", "completed")

        # Create and display network details panel
        details = f"""[bold]Network ID:[/bold] {network["id"]}
[bold]Name:[/bold] {network["name"]}
[bold]Region:[/bold] {network["region"]}
[bold]Status:[/bold] {network["status"]}
[bold]CIDR:[/bold] {network["cidr"]}
[bold]DNS Servers:[/bold] {", ".join(network["dns_servers"])}
[bold]Created:[/bold] {network["created_at"]}
[bold]Updated:[/bold] {network["updated_at"]}

[bold]Subnets:[/bold]"""

        for subnet in network["subnets"]:
            details += f"\n  • {subnet['id']} - {subnet['cidr']} ({subnet['availability_zone']})"

        panel = Panel(details, title="Network Details", border_style="blue")
        renderer.panel_step(panel)
