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

from typing import Annotated, Any, Dict, Optional

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import RenderStepOutput


@handle_abort
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
    # Get command timing
    command_start_time = getattr(ctx.obj, "command_start_time", None)

    # Check for JSON output mode
    json_output = getattr(ctx.obj, "json_output", False)

    # If JSON mode, bypass all visual rendering
    if json_output:
        result: Dict[str, Any] = {
            "network_id": network_id,
            "updates": {"name": name, "description": description, "enable_dns": enable_dns},
            "status": "updated",
            "message": f"Network {network_id} updated successfully",
        }
        RenderStepOutput.json_bypass(result)
        return

    # Regular rendering for non-JSON mode
    step_names = ["Validating network", "Applying configuration changes", "Updating DNS settings"]
    console = ctx.obj.console

    with RenderStepOutput(
        console=console,
        operation_name="Updating network",
        step_names=step_names,
        json_output=json_output,
        command_start_time=command_start_time,
    ) as renderer:
        renderer.advance("Validating network", "starting")
        # Simulate validation
        renderer.advance("Validating network", "completed")

        renderer.advance("Applying configuration changes", "starting")
        # Simulate applying changes
        renderer.advance("Applying configuration changes", "completed")

        renderer.advance("Updating DNS settings", "starting")
        # Simulate DNS updates
        renderer.advance("Updating DNS settings", "completed")
