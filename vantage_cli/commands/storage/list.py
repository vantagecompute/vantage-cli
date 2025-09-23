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
"""List storage command."""

from typing import Annotated, Optional

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import RenderStepOutput


@handle_abort
@attach_settings
async def list_storage(
    ctx: typer.Context,
    zone: Annotated[
        Optional[str], typer.Option("--zone", "-z", help="Filter by availability zone")
    ] = None,
    storage_type: Annotated[
        Optional[str], typer.Option("--type", "-t", help="Filter by storage type")
    ] = None,
    status: Annotated[
        Optional[str], typer.Option("--status", "-s", help="Filter by status")
    ] = None,
    limit: Annotated[
        Optional[int],
        typer.Option("--limit", "-l", help="Maximum number of storage volumes to return"),
    ] = 10,
):
    """List all storage volumes."""
    json_output = getattr(ctx.obj, "json_output", False)
    verbose = getattr(ctx.obj, "verbose", False)

    # Get command start time for timing
    command_start_time = getattr(ctx.obj, "command_start_time", None) if ctx.obj else None

    # Mock data
    volumes = [
        {
            "storage_id": "storage-123",
            "name": "web-data-volume",
            "size_gb": 100,
            "storage_type": "ssd",
            "zone": "us-west-2a",
            "status": "available",
            "attached_to": "instance-456",
        },
        {
            "storage_id": "storage-124",
            "name": "backup-volume",
            "size_gb": 500,
            "storage_type": "hdd",
            "zone": "us-west-2b",
            "status": "creating",
            "attached_to": None,
        },
    ]

    # Apply filters
    if zone:
        volumes = [v for v in volumes if v["zone"] == zone]
    if storage_type:
        volumes = [v for v in volumes if v["storage_type"] == storage_type]
    if status:
        volumes = [v for v in volumes if v["status"] == status]

    # Handle JSON output first
    if json_output:
        renderer = RenderStepOutput(
            console=ctx.obj.console,
            operation_name="List Storage Volumes",
            step_names=[],
            verbose=verbose,
            command_start_time=command_start_time,
        )
        return renderer.json_bypass(
            {
                "volumes": volumes[:limit] if limit else volumes,
                "total": len(volumes),
                "filters": {
                    "zone": zone,
                    "storage_type": storage_type,
                    "status": status,
                    "limit": limit,
                },
            }
        )

    renderer = RenderStepOutput(
        console=ctx.obj.console,
        operation_name="List Storage Volumes",
        step_names=["Fetching storage volumes", "Applying filters", "Formatting output"],
        verbose=verbose,
        command_start_time=command_start_time,
    )

    with renderer:
        renderer.complete_step("Fetching storage volumes")
        renderer.complete_step("Applying filters")
        renderer.start_step("Formatting output")

        # Rich console output
        ctx.obj.console.print("💾 Storage Volumes:")
        ctx.obj.console.print()

        for vol in volumes[:limit] if limit else volumes:
            attached = vol["attached_to"] or "unattached"
            ctx.obj.console.print(
                f"  🏷️  [bold blue]{vol['storage_id']}[/bold blue] - {vol['name']}"
            )
            ctx.obj.console.print(
                f"      Size: [cyan]{vol['size_gb']} GB[/cyan] | Type: [yellow]{vol['storage_type']}[/yellow] | Status: [green]{vol['status']}[/green] | Attached: [magenta]{attached}[/magenta]"
            )
            ctx.obj.console.print()

        ctx.obj.console.print(f"📊 Total volumes: {len(volumes)}")

        renderer.complete_step("Formatting output")
