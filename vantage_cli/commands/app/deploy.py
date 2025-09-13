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
"""Deploy and register clusters."""

from typing import Annotated

import typer
from rich.console import Console

from vantage_cli.commands.cluster.utils import get_available_apps, get_cluster_by_name
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def deploy_app(
    ctx: typer.Context,
    app_name: Annotated[
        str, typer.Argument(help="Name of the cluster infrastructure application to deploy")
    ],
    cluster_name: Annotated[
        str, typer.Argument(help="Name of the cluster in Vantage you would like to link to")
    ],
) -> None:
    """Deploy a slurm cluster and link it to a cluster entity in Vantage."""
    try:
        # Get available apps
        available_apps = get_available_apps()

        if app_name not in available_apps:
            console.print(f"[bold red]✗ App '{app_name}' not found[/bold red]")
            console.print(f"\nAvailable apps: {', '.join(available_apps.keys())}")
            console.print("Use [cyan]vantage apps list[/cyan] to see all available applications.")
            raise typer.Exit(1)

        console.print(
            f"[bold blue]Deploying app '{app_name}' to cluster '{cluster_name}'...[/bold blue]"
        )

        # Get cluster data
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

            # Call the deploy function with cluster data
            await deploy_function(ctx, cluster_data)

            console.print(
                f"[bold green]✓ App '{app_name}' deployed successfully to cluster '{cluster_name}'![/bold green]"
            )
        else:
            console.print(
                f"[bold red]✗ App '{app_name}' does not have a deploy function[/bold red]"
            )
            raise typer.Exit(1)

    except typer.Exit:
        # Re-raise typer.Exit to maintain exit codes
        raise
    except Exception as e:
        console.print(f"[bold red]✗ Error deploying app '{app_name}': {e}[/bold red]")
        raise typer.Exit(1)
