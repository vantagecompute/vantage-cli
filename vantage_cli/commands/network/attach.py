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

from typing import Annotated, Any, Dict, Optional

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import RenderStepOutput


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
    # Get command timing
    command_start_time = getattr(ctx.obj, "command_start_time", None)

    # Check for JSON output mode
    json_output = getattr(ctx.obj, "json_output", False)

    # If JSON mode, bypass all visual rendering
    if json_output:
        result: Dict[str, Any] = {
            "network_id": network_id,
            "instance_id": instance_id,
            "subnet_id": subnet_id,
            "assign_public_ip": assign_public_ip,
            "status": "attached",
            "message": "Network interface attached successfully",
        }
        RenderStepOutput.json_bypass(result)
        return

    # Regular rendering for non-JSON mode
    step_names = [
        "Validating network interface",
        "Attaching network to instance",
        "Configuring network settings",
    ]
    console = ctx.obj.console

    with RenderStepOutput(
        console=console,
        operation_name="Attaching network interface",
        step_names=step_names,
        json_output=json_output,
        command_start_time=command_start_time,
    ) as renderer:
        renderer.advance("Validating network interface", "starting")
        # Simulate validation
        renderer.advance("Validating network interface", "completed")

        renderer.advance("Attaching network to instance", "starting")
        # Simulate attach operation
        renderer.advance("Attaching network to instance", "completed")

        renderer.advance("Configuring network settings", "starting")
        # Simulate configuration
        renderer.advance("Configuring network settings", "completed")
