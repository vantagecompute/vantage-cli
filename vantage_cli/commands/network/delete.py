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
"""Delete network command."""

from typing import Annotated, Any, Dict

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import RenderStepOutput


@handle_abort
@attach_settings
async def delete_network(
    ctx: typer.Context,
    network_id: Annotated[str, typer.Argument(help="ID of the network to delete")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation prompt")] = False,
):
    """Delete a virtual network."""
    # Get command timing
    command_start_time = getattr(ctx.obj, "command_start_time", None)

    # Check for JSON output mode
    json_output = getattr(ctx.obj, "json_output", False)

    # If JSON mode, bypass all visual rendering
    if json_output:
        result: Dict[str, Any] = {
            "network_id": network_id,
            "status": "deleted",
            "force": force,
            "message": f"Network {network_id} deleted successfully",
        }
        RenderStepOutput.json_bypass(result)
        return

    # Regular rendering for non-JSON mode
    step_names = [
        "Validating network",
        "Detaching instances",
        "Removing subnets",
        "Deleting network",
    ]
    if force:
        step_names = ["Validating network", "Force deleting network"]

    console = ctx.obj.console

    with RenderStepOutput(
        console=console,
        operation_name="Deleting network",
        step_names=step_names,
        json_output=json_output,
        command_start_time=command_start_time,
    ) as renderer:
        renderer.advance("Validating network", "starting")
        # Simulate validation
        renderer.advance("Validating network", "completed")

        if force:
            renderer.advance("Force deleting network", "starting")
            # Simulate force deletion
            renderer.advance("Force deleting network", "completed")
        else:
            renderer.advance("Detaching instances", "starting")
            # Simulate detaching instances
            renderer.advance("Detaching instances", "completed")

            renderer.advance("Removing subnets", "starting")
            # Simulate subnet removal
            renderer.advance("Removing subnets", "completed")

            renderer.advance("Deleting network", "starting")
            # Simulate network deletion
            renderer.advance("Deleting network", "completed")
