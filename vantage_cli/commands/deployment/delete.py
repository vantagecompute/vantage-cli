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
"""Delete deployment command for Vantage CLI."""

import typer
from rich.panel import Panel
from rich.prompt import Confirm
from typing_extensions import Annotated

from vantage_cli.apps.common import get_deployments, remove_deployment
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@attach_settings
@handle_abort
async def delete_deployment(
    ctx: typer.Context,
    deployment_id: Annotated[str, typer.Argument(help="Deployment ID to delete")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation prompt")] = False,
) -> None:
    """Delete a deployment and clean up its resources.

    This command will:
    1. Find the deployment by ID
    2. Call the appropriate app-specific cleanup function
    3. Mark the deployment as deleted in the tracking file
    """
    ctx.obj.console.print(Panel("Vantage Deployment Deletion"))

    # Load deployments
    deployments = get_deployments(ctx.obj.console)

    # Find the deployment
    deployment = None
    for dep in deployments:
        if dep.get("deployment_id") == deployment_id:
            deployment = dep
            break

    if not deployment:
        ctx.obj.console.print(f"[red]Error: Deployment with ID '{deployment_id}' not found[/red]")
        raise typer.Exit(code=1)

    # Check if already deleted
    if deployment.get("status") == "deleted":
        ctx.obj.console.print(
            f"[yellow]Deployment '{deployment_id}' is already marked as deleted[/yellow]"
        )
        return

    # Show deployment info
    app_name = deployment.get("app_name", "N/A")
    ctx.obj.console.print(f"[blue]Deployment ID:[/blue] {deployment.get('deployment_id')}")
    ctx.obj.console.print(
        f"[blue]Deployment Name:[/blue] {deployment.get('deployment_name', 'N/A')}"
    )
    ctx.obj.console.print(f"[blue]App Type:[/blue] {app_name}")
    ctx.obj.console.print(f"[blue]Created At:[/blue] {deployment.get('created_at', 'N/A')}")

    # Confirm deletion unless force flag is used
    if not force:
        if not Confirm.ask(
            "\n[red]Are you sure you want to delete this deployment and clean up its resources?[/red]"
        ):
            ctx.obj.console.print("[yellow]Deletion cancelled[/yellow]")
            return

    ctx.obj.console.print(f"\n[blue]Deleting deployment '{deployment_id}'...[/blue]")

    # Call the appropriate cleanup function based on app type
    app_type = deployment.get("app_name")  # Use app_name instead of app_type
    cluster_data = deployment.get("cluster_data", {})

    try:
        if app_type == "slurm-juju-localhost":
            from vantage_cli.apps.slurm_juju_localhost.app import cleanup_juju_localhost

            await cleanup_juju_localhost(ctx, cluster_data)
        elif app_type == "slurm-multipass-localhost":
            from vantage_cli.apps.slurm_multipass_localhost.app import cleanup_multipass_localhost

            await cleanup_multipass_localhost(ctx, cluster_data)
        elif app_type == "slurm-microk8s-localhost":
            from vantage_cli.apps.slurm_microk8s_localhost.app import cleanup_microk8s_localhost

            await cleanup_microk8s_localhost(ctx, cluster_data)
        else:
            ctx.obj.console.print(
                f"[yellow]Warning: Unknown app type '{app_type}', skipping cleanup[/yellow]"
            )

    except Exception as e:
        ctx.obj.console.print(f"[yellow]Warning: Cleanup encountered an error: {e}[/yellow]")
        ctx.obj.console.print("[yellow]Continuing to mark deployment as deleted...[/yellow]")

    # Remove deployment entry from tracking file
    if remove_deployment(deployment_id, ctx.obj.console):
        ctx.obj.console.print(
            f"[green]Successfully deleted deployment '{deployment_id}' and removed from tracking[/green]"
        )
    else:
        ctx.obj.console.print(
            f"[yellow]Warning: Could not remove deployment '{deployment_id}' from tracking file[/yellow]"
        )
