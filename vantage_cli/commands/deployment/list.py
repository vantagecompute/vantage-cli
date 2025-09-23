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
from typing import Optional

import typer
from rich.table import Table
from typing_extensions import Annotated

from vantage_cli.apps.common import load_deployments
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import RenderStepOutput


@attach_settings
@handle_abort
async def list_deployments(
    ctx: typer.Context,
    cloud: Annotated[
        Optional[str],
        typer.Option(
            "--cloud", help="Filter deployments by cloud type (e.g., localhost, aws, gcp)"
        ),
    ] = None,
) -> None:
    """List all active deployments from ~/.vantage-cli/deployments.yaml."""
    # Get JSON flag from context (automatically set by AsyncTyper)
    json_output = getattr(ctx.obj, "json_output", False)
    verbose = getattr(ctx.obj, "verbose", False)

    try:
        # Load deployments from YAML file
        deployments_data = load_deployments(ctx.obj.console)
        active_deployments = {
            dep_id: dep_data
            for dep_id, dep_data in deployments_data["deployments"].items()
            if dep_data.get("status") == "active"
        }

        # Apply cloud filter if specified
        if cloud:
            active_deployments = {
                dep_id: dep_data
                for dep_id, dep_data in active_deployments.items()
                if dep_data.get("cloud", "unknown").lower() == cloud.lower()
            }

        # Get command start time for timing
        command_start_time = getattr(ctx.obj, "command_start_time", None) if ctx.obj else None

        if json_output:
            # JSON output - bypass progress system entirely
            deployments_list = []
            for deployment_id, deployment_data in active_deployments.items():
                deployment_info = {
                    "deployment_id": deployment_id,
                    "deployment_name": deployment_data.get("deployment_name", "unknown"),
                    "app_name": deployment_data.get("app_name", "unknown"),
                    "cluster_name": deployment_data.get("cluster_name", "unknown"),
                    "cluster_id": deployment_data.get("cluster_id", "unknown"),
                    "cloud": deployment_data.get("cloud", "unknown"),
                    "created_at": deployment_data.get("created_at", "unknown"),
                    "status": deployment_data.get("status", "unknown"),
                }
                deployments_list.append(deployment_info)

            renderer = RenderStepOutput(
                console=ctx.obj.console,
                operation_name="Listing deployments",
                step_names=[],
                verbose=verbose,
                command_start_time=command_start_time,
            )
            return renderer.json_bypass(
                {
                    "deployments": deployments_list,
                    "total_count": len(deployments_list),
                    "cloud_filter": cloud,
                }
            )

        # Rich output with progress system
        renderer = RenderStepOutput(
            console=ctx.obj.console,
            operation_name="Listing deployments",
            step_names=["Loading deployment data", "Filtering deployments", "Formatting output"],
            verbose=verbose,
            command_start_time=command_start_time,
        )

        with renderer:
            # Step 1: Data loading (already done)
            renderer.complete_step("Loading deployment data")

            # Step 2: Filtering (already done)
            renderer.complete_step("Filtering deployments")

            # Step 3: Format and display output
            renderer.start_step("Formatting output")

            # Rich table output
            if not active_deployments:
                ctx.obj.console.print("[yellow]No active deployments found.[/yellow]")
                ctx.obj.console.print(
                    "[dim]Use 'vantage deployment create <app> <cluster>' to create a deployment.[/dim]"
                )
                renderer.complete_step("Formatting output")
                return

            table = Table(
                title="Active Deployments", show_header=True, header_style="bold magenta"
            )
            table.add_column("Deployment Name", style="green")
            table.add_column("Deployment ID", style="cyan")
            table.add_column("App", style="blue", width=20)
            table.add_column("Cluster", style="yellow", width=20)
            table.add_column("Cloud", style="bright_blue", width=12)
            table.add_column("Created", style="white", width=20)
            table.add_column("Status", style="magenta", width=10)

            for deployment_id, deployment_data in active_deployments.items():
                deployment_name = deployment_data.get("deployment_name", "unknown")
                app_name = deployment_data.get("app_name", "unknown")
                cluster_name = deployment_data.get("cluster_name", "unknown")
                cloud_name = deployment_data.get("cloud", "unknown")
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
                    deployment_name,
                    deployment_id,
                    app_name,
                    cluster_name,
                    cloud_name,
                    created_at,
                    status,
                )

            renderer.table_step(table)

            # Show summary with cloud filter info if applicable
            summary_msg = f"\n[bold]Found {len(active_deployments)} active deployment(s)"
            if cloud:
                summary_msg += f" for cloud '{cloud}'"
            summary_msg += "[/bold]"
            ctx.obj.console.print(summary_msg)

            renderer.complete_step("Formatting output")

    except Exception as e:
        ctx.obj.console.print(f"[red]Error loading deployments: {e}[/red]")
        raise typer.Exit(1)
