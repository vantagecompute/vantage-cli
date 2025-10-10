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
"""Create new clusters and register them in Vantage."""

from pathlib import Path
from typing import Any, Optional

import click
import typer
from typing_extensions import Annotated

from vantage_cli.apps.utils import get_available_apps
from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.sdk.admin.management.organizations import get_extra_attributes
from vantage_cli.sdk.cluster.crud import cluster_sdk
from vantage_cli.sdk.cluster.schema import Cluster
from vantage_cli.vantage_rest_api_client import attach_vantage_rest_client

from .utils import get_app_choices, get_cloud_choices


@handle_abort
@attach_settings
@attach_persona
@attach_vantage_rest_client
async def create_cluster(
    ctx: typer.Context,
    cluster_name: Annotated[str, typer.Argument(help="Name of the cluster to create")],
    cloud: Annotated[
        str,
        typer.Option(
            "--cloud",
            "-c",
            help="Cloud to use for deployment.",
            case_sensitive=False,
            click_type=click.Choice(get_cloud_choices(), case_sensitive=False),
        ),
    ],
    config_file: Annotated[
        Optional[Path],
        typer.Option(
            "--config-file",
            help="Path to configuration file for cluster creation.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
    app: Annotated[
        Optional[str],
        typer.Option(
            "--app",
            help="Deploy an application after cluster creation.",
            case_sensitive=False,
            click_type=click.Choice(get_app_choices(), case_sensitive=False),
        ),
    ] = None,
):
    """Create a new Vantage cluster."""
    # Use UniversalOutputFormatter for consistent output
    verbose = getattr(ctx.obj, "verbose", False)

    # Ensure we have settings configured
    if not ctx.obj or not ctx.obj.settings:
        raise Abort(
            "No settings configured. Please run 'vantage config set' first.",
            subject="Configuration Required",
            log_message="Settings not configured",
        )

    # Validate cloud provider
    supported_clouds = ctx.obj.settings.supported_clouds
    if cloud not in supported_clouds:
        raise Abort(
            f"Unsupported cloud provider: {cloud}. Supported providers: {', '.join(supported_clouds)}",
            subject="Invalid Cloud Provider",
            log_message=f"Invalid cloud provider: {cloud}",
        )

    # Map cloud provider to GraphQL enum values
    provider_mapping = {
        "localhost": "on_prem",
        "aws": "aws",
        "gcp": "on_prem",  # TODO: Add GCP support to backend
        "azure": "on_prem",  # TODO: Add Azure support to backend
        "on-premises": "on_prem",
    }

    # Build provider-specific attributes
    provider_attributes: Optional[dict[str, Any]] = None
    if cloud == "aws":
        # For AWS, we need providerAttributes (camelCase for GraphQL)
        # This is a simplified example - in practice you'd need to collect more details
        provider_attributes = {
            "aws": {
                "headNodeInstanceType": "t3.medium",  # camelCase for GraphQL
                "keyPair": "default",  # This should be configurable
                "cloudAccountId": 1,  # This should come from user's cloud account
                "regionName": "us_west_2",
            }
        }

    # If config file is provided, read and parse it
    if config_file:
        try:
            import json

            config_data = json.loads(config_file.read_text())
            # Merge config file data
            if "providerAttributes" in config_data:
                provider_attributes = config_data["providerAttributes"]
        except Exception as e:
            raise Abort(
                f"Failed to read configuration file: {e}",
                subject="Configuration File Error",
                log_message=f"Config file error: {e}",
            )

    try:
        # Use SDK to create cluster
        if verbose:
            ctx.obj.console.print(
                f"[bold blue]Creating cluster '{cluster_name}' on {cloud}...[/bold blue]"
            )

        # Create cluster using SDK
        cluster = await cluster_sdk.create_cluster(
            ctx=ctx,
            name=cluster_name,
            provider=provider_mapping.get(cloud, "on_prem"),
            description=f"Cluster {cluster_name} created via CLI",
            provider_attributes=provider_attributes,
        )

        # Use formatter to render the created cluster
        ctx.obj.formatter.render_create(
            data=cluster.model_dump(),
            resource_name="Cluster",
        )

        # Deploy application if --app option was provided
        if app:
            await deploy_app_to_cluster(ctx, cluster, app)

    except Abort:
        # Re-raise Abort exceptions as they contain user-friendly messages
        raise
    except Exception as e:
        raise Abort(
            "An unexpected error occurred while creating the cluster.",
            subject="Unexpected Error",
            log_message=f"Unexpected error: {e}",
        )


async def deploy_app_to_cluster(ctx: typer.Context, cluster: Cluster, app_name: str):
    """Deploy an application to the newly created cluster."""
    try:
        # Get available apps
        available_apps = get_available_apps()

        if app_name not in available_apps:
            ctx.obj.console.print(f"[bold red]✗ App '{app_name}' not found[/bold red]")
            return

        ctx.obj.console.print(
            f"[bold blue]Deploying app '{app_name}' to cluster '{cluster.name}'...[/bold blue]"
        )

        # Get the app info
        app_info = available_apps[app_name]

        # Check if this is a function-based app or class-based app
        if "create_function" in app_info:
            # Function-based app
            create_function = app_info["create_function"]

            # Fetch sssd_binder_password from organization extra attributes
            if extra_attrs := await get_extra_attributes(ctx):
                if sssd_binder_password := extra_attrs.get("sssd_binder_password"):
                    cluster.sssd_binder_password = sssd_binder_password

            await create_function(ctx, cluster)

            ctx.obj.console.print(
                f"[bold green]✓ App '{app_name}' deployed successfully![/bold green]"
            )

        elif "instance" in app_info:
            # Class-based app
            app_instance = app_info["instance"]

            # Check if the app has a deploy method
            if hasattr(app_instance, "create"):
                # Call the app's create method
                await app_instance.create(ctx, cluster)

                ctx.obj.console.print(
                    f"[bold green]✓ App '{app_name}' deployed successfully![/bold green]"
                )
            else:
                ctx.obj.console.print(
                    f"[bold yellow]! App '{app_name}' does not support automatic deployment[/bold yellow]"
                )
                ctx.obj.console.print(
                    "[dim]You can manually deploy this app using the appropriate commands.[/dim]"
                )
        else:
            ctx.obj.console.print(
                f"[bold yellow]! App '{app_name}' does not support automatic deployment[/bold yellow]"
            )
            ctx.obj.console.print(
                "[dim]You can manually deploy this app using the appropriate commands.[/dim]"
            )

    except Exception as e:
        ctx.obj.console.print(f"[bold red]✗ Failed to deploy app '{app_name}': {e}[/bold red]")
        ctx.obj.console.print(
            "[dim]The cluster was created successfully, but app deployment failed.[/dim]"
        )
