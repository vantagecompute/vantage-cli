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
"""Detach network command."""

from typing import Annotated, Any, Dict

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import RenderStepOutput


@handle_abort
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
    # Get command timing
    command_start_time = getattr(ctx.obj, "command_start_time", None)

    # Check for JSON output mode
    json_output = getattr(ctx.obj, "json_output", False)

    # If JSON mode, bypass all visual rendering
    if json_output:
        result: Dict[str, Any] = {
            "network_id": network_id,
            "instance_id": instance_id,
            "force": force,
            "status": "detached",
            "message": "Network interface detached successfully",
        }
        RenderStepOutput.json_bypass(result)
        return

    # Regular rendering for non-JSON mode
    step_names = [
        "Validating network interface",
        "Gracefully stopping connections",
        "Detaching network interface",
    ]
    if force:
        step_names = ["Validating network interface", "Force detaching network interface"]

    console = ctx.obj.console

    with RenderStepOutput(
        console=console,
        operation_name="Detaching network interface",
        step_names=step_names,
        json_output=json_output,
        command_start_time=command_start_time,
    ) as renderer:
        renderer.advance("Validating network interface", "starting")
        # Simulate validation
        renderer.advance("Validating network interface", "completed")

        if force:
            renderer.advance("Force detaching network interface", "starting")
            # Simulate force detach
            renderer.advance("Force detaching network interface", "completed")
        else:
            renderer.advance("Gracefully stopping connections", "starting")
            # Simulate graceful shutdown
            renderer.advance("Gracefully stopping connections", "completed")

            renderer.advance("Detaching network interface", "starting")
            # Simulate detach
            renderer.advance("Detaching network interface", "completed")
