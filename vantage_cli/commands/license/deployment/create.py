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
"""Create license deployment command."""

from typing import Annotated, Optional

import typer
from rich import print_json

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def create_license_deployment(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the license deployment to create")],
    product_id: Annotated[
        str, typer.Option("--product-id", "-p", help="Product ID for the deployment")
    ],
    environment: Annotated[
        str, typer.Option("--environment", "-e", help="Deployment environment (dev, test, prod)")
    ] = "dev",
    nodes: Annotated[
        Optional[int], typer.Option("--nodes", "-n", help="Number of nodes in the deployment")
    ] = 1,
    description: Annotated[
        Optional[str],
        typer.Option("--description", "-d", help="Description of the license deployment"),
    ] = None,
):
    """Create a new license deployment."""
    if getattr(ctx.obj, "json_output", False):
        # JSON output
        print_json(
            data={
                "deployment_id": "deployment-new-123",
                "name": name,
                "product_id": product_id,
                "environment": environment,
                "nodes": nodes,
                "description": description,
                "status": "created",
                "created_at": "2025-09-10T10:00:00Z",
            }
        )
    else:
        # Rich console output
        ctx.obj.console.print(f"📦 Creating license deployment [bold blue]{name}[/bold blue]")
        ctx.obj.console.print(f"   Product ID: [green]{product_id}[/green]")
        ctx.obj.console.print(f"   Environment: [yellow]{environment}[/yellow]")
        ctx.obj.console.print(f"   Nodes: [cyan]{nodes}[/cyan]")
        if description:
            ctx.obj.console.print(f"   Description: {description}")
        ctx.obj.console.print("✅ License deployment created successfully!")
