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
"""Create network command."""

import uuid
from typing import Annotated, Any, Dict, Optional

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import RenderStepOutput


@handle_abort
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
    # Get command timing
    command_start_time = getattr(ctx.obj, "command_start_time", None)

    # Check for JSON output mode
    json_output = getattr(ctx.obj, "json_output", False)

    # Generate network ID and prepare result
    network_id = f"net-{str(uuid.uuid4())[:8]}"
    default_region = region or "us-west-2"

    result: Dict[str, Any] = {
        "id": network_id,
        "name": name,
        "cidr": cidr,
        "region": default_region,
        "enable_dns": enable_dns,
        "description": description,
        "status": "creating",
        "created_at": "2025-01-15T12:00:00Z",
    }

    # If JSON mode, bypass all visual rendering
    if json_output:
        RenderStepOutput.json_bypass(result)
        return

    # Regular rendering for non-JSON mode
    step_names = [
        "Validating CIDR block",
        "Creating network infrastructure",
        "Configuring DNS settings",
        "Finalizing network",
    ]
    console = ctx.obj.console

    with RenderStepOutput(
        console=console,
        operation_name="Creating network",
        step_names=step_names,
        json_output=json_output,
        command_start_time=command_start_time,
    ) as renderer:
        renderer.advance("Validating CIDR block", "starting")
        # Simulate validation
        renderer.advance("Validating CIDR block", "completed")

        renderer.advance("Creating network infrastructure", "starting")
        # Simulate infrastructure creation
        renderer.advance("Creating network infrastructure", "completed")

        renderer.advance("Configuring DNS settings", "starting")
        # Simulate DNS configuration
        renderer.advance("Configuring DNS settings", "completed")

        renderer.advance("Finalizing network", "starting")
        # Simulate finalization
        renderer.advance("Finalizing network", "completed")
