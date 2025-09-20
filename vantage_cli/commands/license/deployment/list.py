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
"""List license deployments command."""

from typing import Annotated, Optional

import typer
from rich import print_json

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def list_license_deployments(
    ctx: typer.Context,
    environment: Annotated[
        Optional[str], typer.Option("--environment", "-e", help="Filter by environment")
    ] = None,
    status: Annotated[
        Optional[str], typer.Option("--status", "-s", help="Filter by status")
    ] = None,
    limit: Annotated[
        Optional[int],
        typer.Option("--limit", "-l", help="Maximum number of deployments to return"),
    ] = 10,
):
    """List all license deployments."""
    if getattr(ctx.obj, "json_output", False):
        # JSON output
        deployments = [
            {
                "deployment_id": "deployment-123",
                "name": "web-app-deployment",
                "product_id": "product-456",
                "environment": "prod",
                "nodes": 5,
                "status": "active",
                "licenses_allocated": 50,
                "licenses_used": 35,
            },
            {
                "deployment_id": "deployment-124",
                "name": "api-deployment",
                "product_id": "product-789",
                "environment": "dev",
                "nodes": 2,
                "status": "inactive",
                "licenses_allocated": 20,
                "licenses_used": 0,
            },
        ]

        # Apply filters
        if environment:
            deployments = [d for d in deployments if d["environment"] == environment]
        if status:
            deployments = [d for d in deployments if d["status"] == status]

        print_json(
            data={
                "deployments": deployments[:limit] if limit else deployments,
                "total": len(deployments),
                "filters": {"environment": environment, "status": status, "limit": limit},
            }
        )
    else:
        # Rich console output
        ctx.obj.console.print("📦 License Deployments:")
        ctx.obj.console.print()

        deployments = [
            ("deployment-123", "web-app-deployment", "prod", "active", "50/35"),
            ("deployment-124", "api-deployment", "dev", "inactive", "20/0"),
        ]

        for dep_id, name, env, stat, licenses in deployments:
            ctx.obj.console.print(f"  🏷️  [bold blue]{dep_id}[/bold blue] - {name}")
            ctx.obj.console.print(
                f"      Environment: [cyan]{env}[/cyan] | Status: [green]{stat}[/green] | Licenses: [yellow]{licenses}[/yellow]"
            )
            ctx.obj.console.print()

        ctx.obj.console.print(f"📊 Total deployments: {len(deployments)}")
