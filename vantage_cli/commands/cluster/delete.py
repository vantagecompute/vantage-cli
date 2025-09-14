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
"""Delete cluster command for Vantage CLI."""

from typing import Any, Optional

import typer
from loguru import logger
from typing_extensions import Annotated

from vantage_cli.apps.common import list_deployments_by_cluster, remove_deployment
from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.gql_client import create_async_graphql_client

from .render import render_cluster_deletion_result


@handle_abort
@attach_settings
async def delete_cluster(
    ctx: typer.Context,
    cluster_name: Annotated[str, typer.Argument(help="Name of the cluster to delete")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation prompt")] = False,
    app: Annotated[
        Optional[str],
        typer.Option(
            "--app",
            help="Cleanup the specified app deployment (e.g., slurm-juju-localhost, slurm-multipass-localhost, slurm-microk8s-localhost)",
        ),
    ] = None,
):
    """Delete a Vantage cluster."""
    # Get JSON flag from context (automatically set by AsyncTyper)
    json_output = getattr(ctx.obj, "json_output", False) if ctx.obj else False
    # Get effective JSON output setting
    effective_json = get_effective_json_output(ctx, json_output)

    # Confirmation prompt unless force is used
    if not force and not effective_json:
        from rich.console import Console
        from rich.prompt import Confirm

        console = Console()
        console.print(
            f"\n[yellow]⚠️  You are about to delete cluster '[bold red]{cluster_name}[/bold red]'[/yellow]"
        )
        console.print("[yellow]This action cannot be undone![/yellow]")

        if not Confirm.ask("Are you sure you want to proceed?"):
            console.print("[dim]Deletion cancelled.[/dim]")
            return

    # GraphQL mutation for deleting a cluster
    delete_mutation = """
    mutation deleteCluster($clusterName: String!) {
        deleteCluster(clusterName: $clusterName) {
            ... on ClusterDeleted {
                message
            }
            ... on ClusterNotFound {
                message
            }
            ... on InvalidProviderInput {
                message
            }
            ... on UnexpectedBehavior {
                message
            }
        }
    }
    """

    try:
        # Create async GraphQL client
        profile = getattr(ctx.obj, "profile", "default")
        graphql_client = create_async_graphql_client(ctx.obj.settings, profile)

        # Prepare deletion variables
        delete_variables = {"clusterName": cluster_name}

        # Execute the deletion mutation
        logger.debug(f"Deleting cluster: {cluster_name}")
        delete_response = await graphql_client.execute_async(delete_mutation, delete_variables)

        # Extract deletion result
        deletion_data = delete_response.get("deleteCluster", {})

        # Log the response for debugging
        logger.debug(f"Delete response: {deletion_data}")

        # Determine success - if we get any response it likely succeeded
        # The GraphQL union types make it tricky to detect success vs failure
        success = bool(deletion_data)  # If we got a response without error, consider it success

        # If cluster deletion was successful and app cleanup was requested
        if success and app:
            await _cleanup_app_deployments(cluster_name, app, effective_json)

        # Render deletion result
        render_cluster_deletion_result(
            cluster_name=cluster_name,
            success=success,
            json_output=effective_json,
        )

    except Abort:
        # Re-raise Abort exceptions as they contain user-friendly messages
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting cluster '{cluster_name}': {e}")
        raise Abort(
            f"An unexpected error occurred while deleting cluster '{cluster_name}'.",
            subject="Unexpected Error",
            log_message=f"Unexpected error: {e}",
        )


async def _call_app_cleanup_function(app: str, cluster_data: dict[str, Any]) -> None:
    """Call the appropriate cleanup function based on app type."""
    if app == "slurm-juju-localhost":
        from vantage_cli.apps.slurm_juju_localhost.app import cleanup_juju_localhost

        await cleanup_juju_localhost(cluster_data)
    elif app == "slurm-multipass-localhost":
        from vantage_cli.apps.slurm_multipass_localhost.app import (
            cleanup_multipass_localhost,
        )

        await cleanup_multipass_localhost(cluster_data)
    elif app == "slurm-microk8s-localhost":
        from vantage_cli.apps.slurm_microk8s_localhost.app import (
            cleanup_microk8s_localhost,
        )

        await cleanup_microk8s_localhost(cluster_data)
    else:
        raise ValueError(f"Unknown app type: {app}")


async def _cleanup_single_deployment(
    deployment_id: str, deployment: dict[str, Any], app: str, json_output: bool
) -> bool:
    """Clean up a single deployment and return True if successful."""
    from rich.console import Console

    console = Console()

    try:
        if not json_output:
            console.print(f"[blue]Cleaning up deployment: {deployment_id}[/blue]")

        # Get cluster data for cleanup functions
        cluster_data = deployment.get("cluster_data", {})

        # Call the appropriate cleanup function
        try:
            await _call_app_cleanup_function(app, cluster_data)
        except ValueError:
            if not json_output:
                console.print(
                    f"[yellow]Warning: Unknown app type '{app}', skipping cleanup[/yellow]"
                )
            return False

        # Remove deployment entry from tracking file
        if remove_deployment(deployment_id):
            if not json_output:
                console.print(f"[green]✓ Cleaned up deployment '{deployment_id}'[/green]")
            return True
        else:
            if not json_output:
                console.print(
                    f"[yellow]Warning: Could not remove deployment '{deployment_id}' from tracking[/yellow]"
                )
            return False

    except Exception as e:
        if not json_output:
            console.print(
                f"[yellow]Warning: Cleanup of deployment '{deployment_id}' failed: {e}[/yellow]"
            )
        return False


async def _cleanup_app_deployments(cluster_name: str, app: str, json_output: bool) -> None:
    """Clean up app deployments for a specific cluster.

    Args:
        cluster_name: Name of the cluster
        app: Name of the app to clean up (e.g., slurm-juju-localhost)
        json_output: Whether to output JSON or rich console messages
    """
    from rich.console import Console

    console = Console()

    if not json_output:
        console.print(
            f"\n[blue]Cleaning up '{app}' deployments for cluster '{cluster_name}'...[/blue]"
        )

    # Find deployments for this cluster
    cluster_deployments = list_deployments_by_cluster(cluster_name)

    # Filter to only the specified app type
    app_deployments = {
        dep_id: dep_data
        for dep_id, dep_data in cluster_deployments.items()
        if dep_data.get("app_name") == app
    }

    if not app_deployments:
        if not json_output:
            console.print(
                f"[yellow]No '{app}' deployments found for cluster '{cluster_name}'[/yellow]"
            )
        return

    cleanup_count = 0
    for deployment_id, deployment in app_deployments.items():
        if await _cleanup_single_deployment(deployment_id, deployment, app, json_output):
            cleanup_count += 1

    if not json_output:
        if cleanup_count > 0:
            console.print(
                f"[green]✓ Successfully cleaned up {cleanup_count} '{app}' deployment(s)[/green]"
            )
        else:
            console.print(f"[yellow]No '{app}' deployments were cleaned up[/yellow]")
