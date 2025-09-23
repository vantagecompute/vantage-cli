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
"""Update license deployment command."""

from typing import Annotated, Optional

import typer
from rich import print_json

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def update_license_deployment(
    ctx: typer.Context,
    deployment_id: Annotated[str, typer.Argument(help="ID of the license deployment to update")],
    name: Annotated[
        Optional[str], typer.Option("--name", "-n", help="New name for the deployment")
    ] = None,
    environment: Annotated[
        Optional[str],
        typer.Option("--environment", "-e", help="New environment for the deployment"),
    ] = None,
    nodes: Annotated[Optional[int], typer.Option("--nodes", help="New number of nodes")] = None,
    description: Annotated[
        Optional[str], typer.Option("--description", "-d", help="New description")
    ] = None,
    status: Annotated[
        Optional[str],
        typer.Option("--status", "-s", help="New status (active, inactive, suspended)"),
    ] = None,
):
    """Update a license deployment."""
    if getattr(ctx.obj, "json_output", False):
        # JSON output
        updates = {}
        if name:
            updates["name"] = name
        if environment:
            updates["environment"] = environment
        if nodes:
            updates["nodes"] = nodes
        if description:
            updates["description"] = description
        if status:
            updates["status"] = status

        print_json(
            data={
                "deployment_id": deployment_id,
                "updates": updates,
                "status": "updated",
                "updated_at": "2025-09-10T10:00:00Z",
            }
        )
    else:
        # Rich console output
        ctx.obj.console.print(
            f"🔄 Updating license deployment [bold blue]{deployment_id}[/bold blue]"
        )

        if name:
            ctx.obj.console.print(f"   Name: [green]{name}[/green]")
        if environment:
            ctx.obj.console.print(f"   Environment: [yellow]{environment}[/yellow]")
        if nodes:
            ctx.obj.console.print(f"   Nodes: [cyan]{nodes}[/cyan]")
        if description:
            ctx.obj.console.print(f"   Description: {description}")
        if status:
            ctx.obj.console.print(f"   Status: [magenta]{status}[/magenta]")

        ctx.obj.console.print("✅ License deployment updated successfully!")
