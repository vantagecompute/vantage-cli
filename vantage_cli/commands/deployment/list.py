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
"""List available applications and active deployments."""

from datetime import datetime

import typer
from rich.table import Table

from vantage_cli.apps.common import load_deployments
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.format import render_json


@attach_settings
@handle_abort
async def list_deployments(
    ctx: typer.Context,
) -> None:
    """List all active deployments from ~/.vantage-cli/deployments.yaml."""
    # Get JSON flag from context (automatically set by AsyncTyper)
    json_output = getattr(ctx.obj, "json_output", False) if ctx.obj else False

    try:
        # Load deployments from YAML file
        deployments_data = load_deployments(ctx.obj.console)
        active_deployments = {
            dep_id: dep_data
            for dep_id, dep_data in deployments_data["deployments"].items()
            if dep_data.get("status") == "active"
        }

        if json_output:
            # Format for JSON output
            deployments_list = []
            for deployment_id, deployment_data in active_deployments.items():
                deployment_info = {
                    "id": deployment_id,
                    "deployment_name": deployment_data.get("deployment_name", "unknown"),
                    "app_name": deployment_data.get("app_name", "unknown"),
                    "cluster_name": deployment_data.get("cluster_name", "unknown"),
                    "cluster_id": deployment_data.get("cluster_id", "unknown"),
                    "created_at": deployment_data.get("created_at", "unknown"),
                    "status": deployment_data.get("status", "unknown"),
                }
                deployments_list.append(deployment_info)

            render_json({"deployments": deployments_list})
            return

        # Rich table output
        if not active_deployments:
            ctx.obj.console.print("[yellow]No active deployments found.[/yellow]")
            ctx.obj.console.print(
                "[dim]Use 'vantage deployment create <app> <cluster>' to create a deployment.[/dim]"
            )
            return

        table = Table(title="Active Deployments", show_header=True, header_style="bold magenta")
        table.add_column("Deployment Name", style="green")
        table.add_column("Deployment ID", style="cyan")
        table.add_column("App", style="blue", width=20)
        table.add_column("Cluster", style="yellow", width=20)
        table.add_column("Created", style="white", width=20)
        table.add_column("Status", style="magenta", width=10)

        for deployment_id, deployment_data in active_deployments.items():
            deployment_name = deployment_data.get("deployment_name", "unknown")
            app_name = deployment_data.get("app_name", "unknown")
            cluster_name = deployment_data.get("cluster_name", "unknown")
            created_at = deployment_data.get("created_at", "unknown")
            status = deployment_data.get("status", "unknown")

            # Format the created_at timestamp if it's an ISO format
            if created_at != "unknown":
                try:
                    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    created_at = dt.strftime("%Y-%m-%d %H:%M")
                except (ValueError, AttributeError):
                    # Keep original if parsing fails
                    pass

            table.add_row(
                deployment_name, deployment_id, app_name, cluster_name, created_at, status
            )

        ctx.obj.console.print(table)
        ctx.obj.console.print(
            f"\n[bold]Found {len(active_deployments)} active deployment(s)[/bold]"
        )

    except Exception as e:
        ctx.obj.console.print(f"[bold red]Error listing deployments: {e}[/bold red]")
        raise typer.Exit(1)
