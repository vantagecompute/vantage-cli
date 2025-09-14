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
"""Get license deployment command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort

console = Console()


@handle_abort
@attach_settings
async def get_license_deployment(
    ctx: typer.Context,
    deployment_id: Annotated[str, typer.Argument(help="ID of the license deployment to retrieve")],
):
    """Get details of a specific license deployment."""
    if get_effective_json_output(ctx):
        # JSON output
        print_json(
            data={
                "deployment_id": deployment_id,
                "name": "web-app-deployment",
                "product_id": "product-456",
                "environment": "prod",
                "nodes": 5,
                "status": "active",
                "description": "Production deployment for web application",
                "created_at": "2025-09-01T09:00:00Z",
                "updated_at": "2025-09-10T10:00:00Z",
                "licenses_allocated": 50,
                "licenses_used": 35,
            }
        )
    else:
        # Rich console output
        console.print(f"📦 License Deployment: [bold blue]{deployment_id}[/bold blue]")
        console.print("   Name: [green]web-app-deployment[/green]")
        console.print("   Product ID: [yellow]product-456[/yellow]")
        console.print("   Environment: [cyan]prod[/cyan]")
        console.print("   Nodes: [magenta]5[/magenta]")
        console.print("   Status: [green]active[/green]")
        console.print("   Description: Production deployment for web application")
        console.print("   Licenses Allocated: [blue]50[/blue]")
        console.print("   Licenses Used: [yellow]35[/yellow]")
        console.print("   Created: 2025-09-01T09:00:00Z")
        console.print("   Updated: 2025-09-10T10:00:00Z")
