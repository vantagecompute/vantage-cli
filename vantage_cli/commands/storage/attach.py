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
"""Attach storage command."""

from typing import Annotated, Optional

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import RenderStepOutput


@handle_abort
@attach_settings
async def attach_storage(
    ctx: typer.Context,
    storage_id: Annotated[str, typer.Argument(help="ID of the storage volume to attach")],
    instance_id: Annotated[str, typer.Argument(help="ID of the instance to attach storage to")],
    mount_point: Annotated[
        Optional[str], typer.Option("--mount-point", "-m", help="Mount point for the storage")
    ] = "/data",
    read_only: Annotated[
        bool, typer.Option("--read-only", "-r", help="Attach storage in read-only mode")
    ] = False,
):
    """Attach a storage volume to an instance."""
    json_output = getattr(ctx.obj, "json_output", False)
    verbose = getattr(ctx.obj, "verbose", False)

    # Get command start time for timing
    command_start_time = getattr(ctx.obj, "command_start_time", None) if ctx.obj else None

    # Mock attachment response data
    attach_data = {
        "storage_id": storage_id,
        "instance_id": instance_id,
        "mount_point": mount_point,
        "read_only": read_only,
        "status": "attached",
        "attached_at": "2025-09-10T10:00:00Z",
        "device_path": "/dev/xvdf",
    }

    # Create renderer once
    renderer = RenderStepOutput(
        console=ctx.obj.console,
        operation_name=f"Attach Storage '{storage_id}'",
        step_names=[]
        if json_output
        else ["Validating parameters", "Attaching storage volume", "Formatting output"],
        verbose=verbose,
        command_start_time=command_start_time,
    )

    # Handle JSON output first
    if json_output:
        return renderer.json_bypass(attach_data)

    with renderer:
        renderer.complete_step("Validating parameters")
        renderer.complete_step("Attaching storage volume")
        renderer.start_step("Formatting output")

        ctx.obj.console.print(
            f"📎 Attaching storage volume [bold blue]{storage_id}[/bold blue] to instance [bold green]{instance_id}[/bold green]"
        )
        ctx.obj.console.print(f"   Mount Point: [yellow]{mount_point}[/yellow]")
        ctx.obj.console.print(f"   Read-Only: [cyan]{read_only}[/cyan]")
        ctx.obj.console.print("   Device Path: [magenta]/dev/xvdf[/magenta]")
        ctx.obj.console.print("✅ Storage volume attached successfully!")

        renderer.complete_step("Formatting output")
