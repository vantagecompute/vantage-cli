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

import logging
from pathlib import Path
from typing import Any, Optional

import click
import typer
from typing_extensions import Annotated

from vantage_cli.auth import attach_persona
from vantage_cli.clouds.constants import DEV_SSSD_BINDER_PASSWORD
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.sdk.cloud.crud import cloud_sdk
from vantage_cli.sdk.cluster.crud import cluster_sdk
from vantage_cli.sdk.cluster.schema import Cluster
from vantage_cli.vantage_rest_api_client import attach_vantage_rest_client

from .utils import get_cloud_choices

logger = logging.getLogger(__name__)


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

    # Note: Cloud provider validation is already done by click.Choice in the parameter definition
    # No need for additional validation here

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

        # Get Cloud object to extract vantage_provider_label
        cloud_obj = cloud_sdk.get(cloud)
        if not cloud_obj:
            raise Abort(
                f"Cloud '{cloud}' not found",
                subject="Cloud Not Found",
                log_message=f"Cloud not found: {cloud}",
            )

        # Create cluster using SDK
        cluster = await cluster_sdk.create_cluster(
            ctx=ctx,
            name=cluster_name,
            provider=cloud_obj.vantage_provider_label,
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
            f"An unexpected error occurred while creating the cluster.\n\nError details: {type(e).__name__}: {e}",
            subject="Unexpected Error",
            log_message=f"Unexpected error: {e}",
        )


async def deploy_app_to_cluster(ctx: typer.Context, cluster: Cluster, app_name: str):
    """Deploy an application to the newly created cluster."""
    try:
        # Import SDK here to avoid module-level initialization
        from vantage_cli.sdk.cloud_credential.crud import cloud_credential_sdk
        from vantage_cli.sdk.deployment_app import deployment_app_sdk

        available_apps_list = deployment_app_sdk.list()
        available_apps = {app.name: app for app in available_apps_list}

        if app_name not in available_apps:
            ctx.obj.console.print(f"[bold red]✗ App '{app_name}' not found[/bold red]")
            ctx.obj.console.print(f"[dim]Available apps: {', '.join(available_apps.keys())}[/dim]")
            return

        logger.info(
            f"[bold blue]Deploying app '{app_name}' to cluster '{cluster.name}'...[/bold blue]"
        )

        # Get the app
        app = available_apps[app_name]

        # Check if app has a module with create function
        if app.module and hasattr(app.module, "create"):
            # Initialize cloud-specific SDK if needed
            if app.cloud == "cudo-compute":
                from cudo_compute_sdk import CudoComputeSDK

                # Get default credential for Cudo Compute
                cudo_credential = cloud_credential_sdk.get_default(cloud_name="cudo-compute")
                if cudo_credential is None:
                    logger.error(
                        "[bold red]✗ No default credential found for 'cudo-compute'[/bold red]"
                    )
                    logger.info(
                        "[dim]Run: vantage cloud credential create --cloud cudo-compute[/dim]"
                    )
                    return

                # Initialize SDK and attach to context
                ctx.obj.cudo_sdk = CudoComputeSDK(
                    api_key=cudo_credential.credentials_data["api_key"]
                )

            # Function-based app
            create_function = getattr(app.module, "create")

            # Fetch sssd_binder_password from organization extra attributes
            if not cluster.sssd_binder_password:
                logger.warning(
                    "[bold yellow]⚠ Using default sssd_binder_password - consider configuring organization settings[/bold yellow]"
                )
                cluster.sssd_binder_password = DEV_SSSD_BINDER_PASSWORD

            # Call the create function
            logger.info(f"[dim]Calling {app.name}.create()...[/dim]")
            result = await create_function(ctx, cluster)

            # Check if the function returned an error exit code
            if isinstance(result, typer.Exit) and result.exit_code != 0:
                logger.error(
                    f"[bold red]✗ App '{app_name}' deployment failed (exit code {result.exit_code})[/bold red]"
                )
                logger.info(
                    "[dim]The cluster was created successfully, but app deployment encountered an error.[/dim]"
                )
            elif isinstance(result, typer.Exit) and result.exit_code == 0:
                logger.info(f"[bold green]✓ App '{app_name}' deployed successfully![/bold green]")
            else:
                # No exit code returned, assume success
                logger.info(f"[bold green]✓ App '{app_name}' deployment completed![/bold green]")
        else:
            logger.warning(
                f"[bold yellow]! App '{app_name}' does not support automatic deployment[/bold yellow]"
            )
            logger.info(
                "[dim]You can manually deploy this app using the appropriate commands.[/dim]"
            )

    except Exception as e:
        import traceback

        logger.error(f"[bold red]✗ Failed to deploy app '{app_name}':[/bold red]")
        logger.error(f"[red]{type(e).__name__}: {e}[/red]")
        if getattr(ctx.obj, "verbose", False):
            logger.error(f"[dim]{traceback.format_exc()}[/dim]")
        logger.error("[dim]The cluster was created successfully, but app deployment failed.[/dim]")
