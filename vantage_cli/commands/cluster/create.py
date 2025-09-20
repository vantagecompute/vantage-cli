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

import uuid
from pathlib import Path
from typing import Any, Optional

import click
import typer
from loguru import logger
from typing_extensions import Annotated

from vantage_cli.apps.common import track_deployment
from vantage_cli.apps.utils import get_available_apps
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.gql_client import create_async_graphql_client

from .render import render_cluster_details
from .utils import get_app_choices, get_cloud_choices


@handle_abort
@attach_settings
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

    # GraphQL mutation for creating a cluster
    create_mutation = """
    mutation createCluster($createClusterInput: CreateClusterInput!) {
        createCluster(createClusterInput: $createClusterInput) {
            ... on Cluster {
                name
                status
                clientId
                description
                ownerEmail
                provider
                cloudAccountId
                creationParameters
            }
            ... on ClusterNameInUse {
                message
            }
            ... on InvalidInput {
                message
            }
            ... on ClusterCouldNotBeDeployed {
                message
            }
            ... on UnexpectedBehavior {
                message
            }
        }
    }
    """

    # Map cloud provider to GraphQL enum values
    provider_mapping = {
        "localhost": "on_prem",
        "aws": "aws",
        "gcp": "on_prem",  # TODO: Add GCP support to backend
        "azure": "on_prem",  # TODO: Add Azure support to backend
        "on-premises": "on_prem",
    }

    # Build the input variables
    cluster_input: dict[str, Any] = {
        "name": cluster_name,
        "description": f"Cluster {cluster_name} created via CLI",
        "provider": provider_mapping.get(cloud, "on_prem"),
    }

    # Add provider-specific attributes if needed
    if cloud == "aws":
        # For AWS, we need providerAttributes (camelCase for GraphQL)
        # This is a simplified example - in practice you'd need to collect more details
        cluster_input["providerAttributes"] = {
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
            # Merge config file data with input
            cluster_input.update(config_data)
        except Exception as e:
            raise Abort(
                f"Failed to read configuration file: {e}",
                subject="Configuration File Error",
                log_message=f"Config file error: {e}",
            )

    variables = {"createClusterInput": cluster_input}

    try:
        # Create async GraphQL client
        logger.debug(f"CTX OBJ: {ctx.obj}")
        graphql_client = create_async_graphql_client(ctx.obj.settings, ctx.obj.profile)

        # Execute the mutation
        logger.debug(f"Creating cluster: {cluster_name}")
        ctx.obj.console.print(
            f"[bold blue]Creating cluster '{cluster_name}' on {cloud}...[/bold blue]"
        )

        response_data = await graphql_client.execute_async(create_mutation, variables)

        # Handle the response
        create_result = response_data.get("createCluster")

        if not create_result:
            raise Abort(
                "No response from server",
                subject="Server Error",
                log_message="Empty response from createCluster mutation",
            )

        # Check for errors in the response
        if "message" in create_result:
            # This is an error response
            error_message = create_result["message"]
            ctx.obj.console.print(
                f"[bold red]Failed to create cluster: {error_message}[/bold red]"
            )
            raise Abort(
                f"Cluster creation failed: {error_message}",
                subject="Cluster Creation Failed",
                log_message=f"GraphQL error: {error_message}",
            )

        # Success case - cluster was created
        if "name" in create_result:
            ctx.obj.console.print(
                f"[bold green]✓ Cluster '{create_result['name']}' created successfully![/bold green]"
            )
            ctx.obj.console.print()

            # Display detailed cluster information
            cluster_table = render_cluster_details(create_result)
            ctx.obj.console.print(cluster_table)

            # Deploy application if --app option was provided
            if app:
                await deploy_app_to_cluster(ctx, create_result, app)

        else:
            ctx.obj.console.print(
                "[bold yellow]Cluster creation initiated but status unclear[/bold yellow]"
            )

    except Abort:
        # Re-raise Abort exceptions as they contain user-friendly messages
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating cluster: {e}")
        raise Abort(
            "An unexpected error occurred while creating the cluster.",
            subject="Unexpected Error",
            log_message=f"Unexpected error: {e}",
        )


async def deploy_app_to_cluster(ctx: typer.Context, cluster_data: dict, app_name: str):
    """Deploy an application to the newly created cluster."""
    try:
        # Get available apps
        available_apps = get_available_apps()

        if app_name not in available_apps:
            ctx.obj.console.print(f"[bold red]✗ App '{app_name}' not found[/bold red]")
            return

        ctx.obj.console.print(
            f"[bold blue]Deploying app '{app_name}' to cluster '{cluster_data['name']}'...[/bold blue]"
        )

        # Get the app info
        app_info = available_apps[app_name]

        # Check if this is a function-based app or class-based app
        if "deploy_function" in app_info:
            # Function-based app
            deploy_function = app_info["deploy_function"]

            # Generate a unique deployment ID and deployment name
            deployment_id = str(uuid.uuid4())
            deployment_name = f"{app_name}-{cluster_data['name']}-{uuid.uuid4().hex[:8]}"

            # Add deployment_name to cluster_data so apps can use it
            cluster_data["deployment_name"] = deployment_name

            await deploy_function(ctx, cluster_data)

            track_deployment(
                deployment_id=deployment_id,
                app_name=app_name,
                cluster_name=cluster_data["name"],
                cluster_data=cluster_data,
                deployment_name=deployment_name,
                console=ctx.obj.console,
                additional_metadata={
                    "deployment_method": "vantage cluster create --app",
                    "cluster_created": True,
                    "app_type": "function-based",
                },
            )

            ctx.obj.console.print(
                f"[bold green]✓ App '{app_name}' deployed successfully![/bold green]"
            )
        elif "instance" in app_info:
            # Class-based app
            app_instance = app_info["instance"]

            # Check if the app has a deploy method
            if hasattr(app_instance, "deploy"):
                # Generate a unique deployment ID and deployment name
                deployment_id = str(uuid.uuid4())
                deployment_name = f"{app_name}-{cluster_data['name']}-{uuid.uuid4().hex[:8]}"

                # Add deployment_name to cluster_data so apps can use it
                cluster_data["deployment_name"] = deployment_name

                # Call the app's deploy method
                await app_instance.deploy(ctx)

                track_deployment(
                    deployment_id=deployment_id,
                    app_name=app_name,
                    cluster_name=cluster_data["name"],
                    cluster_data=cluster_data,
                    deployment_name=deployment_name,
                    console=ctx.obj.console,
                    additional_metadata={
                        "deployment_method": "vantage cluster create --app",
                        "cluster_created": True,
                        "app_type": "class-based",
                    },
                )

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
        logger.error(f"Failed to deploy app '{app_name}': {e}")
        ctx.obj.console.print(f"[bold red]✗ Failed to deploy app '{app_name}': {e}[/bold red]")
        ctx.obj.console.print(
            "[dim]The cluster was created successfully, but app deployment failed.[/dim]"
        )
