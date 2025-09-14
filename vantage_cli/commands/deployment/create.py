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
"""Create and register clusters."""

import uuid
from typing import Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from vantage_cli.apps.common import (
    generate_default_deployment_name,
    generate_dev_cluster_data,
    load_deployments,
    save_deployments,
    track_deployment,
)
from vantage_cli.commands.cluster.utils import get_available_apps, get_cluster_by_name
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort

console = Console()


@attach_settings
@handle_abort
async def create_deployment(
    ctx: typer.Context,
    app_name: Annotated[
        str, typer.Argument(help="Name of the cluster infrastructure application to deploy")
    ],
    cluster_name: Annotated[
        str, typer.Argument(help="Name of the cluster in Vantage you would like to link to")
    ],
    name: Annotated[
        Optional[str],
        typer.Option(
            "--name", help="Custom name for the deployment (default: <app>-<cluster>-<timestamp>)"
        ),
    ] = None,
    dev_run: Annotated[
        bool, typer.Option("--dev-run", help="Use dummy cluster data for local development")
    ] = False,
) -> None:
    """Create a slurm cluster deployment and link it to a cluster entity in Vantage."""
    try:
        # Get available apps
        available_apps = get_available_apps()

        if app_name not in available_apps:
            console.print(f"[bold red]✗ App '{app_name}' not found[/bold red]")
            console.print(f"\nAvailable apps: {', '.join(available_apps.keys())}")
            console.print(
                "Use [cyan]vantage deployment list[/cyan] to see all available applications."
            )
            raise typer.Exit(1)

        console.print(
            f"[bold blue]Creating deployment '{app_name}' for cluster '{cluster_name}'...[/bold blue]"
        )

        # Get cluster data - either from API or generate dummy data
        cluster_data = None
        if dev_run:
            console.print(
                f"[blue]Using dev run mode with dummy cluster data for '{cluster_name}'[/blue]"
            )
            cluster_data = generate_dev_cluster_data(cluster_name)
        else:
            cluster_data = await get_cluster_by_name(ctx, cluster_name)
            if not cluster_data:
                console.print(f"[bold red]✗ Cluster '{cluster_name}' not found[/bold red]")
                raise typer.Exit(1)

        # Get the app info
        app_info = available_apps[app_name]

        # Check if this is a function-based app
        if "deploy_function" in app_info:
            # Function-based app
            deploy_function = app_info["deploy_function"]

            # Generate a unique deployment ID and track the deployment BEFORE calling deploy
            deployment_id = str(uuid.uuid4())
            deployment_name = name or generate_default_deployment_name(app_name, cluster_name)

            # Add deployment_name to cluster_data so apps can use it
            cluster_data["deployment_name"] = deployment_name

            track_deployment(
                deployment_id=deployment_id,
                app_name=app_name,
                cluster_name=cluster_name,
                cluster_data=cluster_data,
                deployment_name=deployment_name,
                additional_metadata={
                    "deployment_method": "vantage deployment create",
                    "dev_run": dev_run,
                },
            )

            try:
                # Add deployment name to cluster data for apps that need it
                cluster_data["deployment_name"] = deployment_name

                # Call the deploy function with cluster data
                await deploy_function(ctx, cluster_data)

                console.print(
                    f"[bold green]✓ Deployment '{app_name}' created successfully for cluster '{cluster_name}'![/bold green]"
                )
            except Exception as e:
                # If deployment fails, mark it as failed but keep the tracking
                deployments_data = load_deployments()
                if deployment_id in deployments_data["deployments"]:
                    deployments_data["deployments"][deployment_id]["status"] = "failed"
                    deployments_data["deployments"][deployment_id]["error"] = str(e)
                    save_deployments(deployments_data)

                console.print(f"[bold red]✗ Deployment failed: {e}[/bold red]")
                raise
        else:
            console.print(
                f"[bold red]✗ App '{app_name}' does not have a deploy function[/bold red]"
            )
            raise typer.Exit(1)

    except typer.Exit:
        # Re-raise typer.Exit to maintain exit codes
        raise
    except Exception as e:
        console.print(f"[bold red]✗ Error creating deployment '{app_name}': {e}[/bold red]")
        raise typer.Exit(1)
