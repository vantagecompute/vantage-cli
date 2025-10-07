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
from rich.console import Console
from typing_extensions import Annotated

from vantage_cli.apps.common import list_deployments_by_cluster, remove_deployment
from vantage_cli.commands.cluster.utils import get_cluster_by_name
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.gql_client import create_async_graphql_client
from vantage_cli.render import RenderStepOutput


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
    json_output = getattr(ctx.obj, "json_output", False)
    verbose = getattr(ctx.obj, "verbose", False)
    command_start_time = getattr(ctx.obj, "command_start_time", None)

    # Confirmation prompt unless force is used
    if not force and not json_output:
        from rich.prompt import Confirm

        ctx.obj.console.print(
            f"\n[yellow]⚠️  You are about to delete cluster '[bold red]{cluster_name}[/bold red]'[/yellow]"
        )
        ctx.obj.console.print("[yellow]This action cannot be undone![/yellow]")

        if not Confirm.ask("Are you sure you want to proceed?"):
            ctx.obj.console.print("[dim]Deletion cancelled.[/dim]")
            return

    step_names = ["Query cluster details", "Delete cluster"]
    if app:
        step_names.append(f"Cleanup {app} deployments")

    renderer = RenderStepOutput(
        console=ctx.obj.console,
        operation_name=f"Deleting cluster '{cluster_name}'",
        step_names=step_names,
        verbose=verbose,
        command_start_time=command_start_time,
        json_output=json_output,
    )

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
        with renderer:
            profile = getattr(ctx.obj, "profile", "default")
            graphql_client = create_async_graphql_client(ctx.obj.settings, profile)

            # Prepare deletion variables
            delete_variables = {"clusterName": cluster_name}

            renderer.start_step("Query cluster details")

            cluster = await get_cluster_by_name(ctx=ctx, cluster_name=cluster_name)
            if not cluster:
                raise Abort(
                    f"No cluster found with name '{cluster_name}'.",
                    subject="Cluster Not Found",
                    log_message=f"Cluster '{cluster_name}' not found",
                )

            renderer.complete_step("Query cluster details")
            renderer.start_step("Delete cluster")

            # Execute the deletion mutation
            logger.debug(f"Deleting cluster: {cluster_name}")
            delete_response = await graphql_client.execute_async(delete_mutation, delete_variables)
            deletion_data = delete_response.get("deleteCluster", {})
            logger.debug(f"Delete response: {deletion_data}")
            
            success = bool(deletion_data)
            if not success:
                raise Abort(
                    f"Failed to delete cluster '{cluster_name}'.",
                    subject="Deletion Failed",
                    log_message=f"Cluster deletion failed: {deletion_data}",
                )
            
            renderer.complete_step("Delete cluster")

            cleanup_result = None
            if app:
                renderer.start_step(f"Cleanup {app} deployments")
                cleanup_result = await _cleanup_app_deployments(
                    ctx, cluster_name, app, json_output, ctx.obj.console
                )
                renderer.complete_step(f"Cleanup {app} deployments")

            if json_output:
                output_data = {
                    "cluster_name": cluster_name,
                    "success": success,
                    "deletion_data": deletion_data,
                }
                if app and cleanup_result is not None:
                    output_data["app_cleanup"] = cleanup_result
                renderer.json_bypass(output_data)
                return

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


async def _call_app_cleanup_function(
    ctx: typer.Context, app: str, cluster_data: dict[str, Any]
) -> None:
    """Call the appropriate cleanup function based on app type."""
    if app == "slurm-juju-localhost":
        from vantage_cli.apps.slurm_lxd_localhost.app import cleanup_juju_localhost

        await cleanup_juju_localhost(ctx, cluster_data)
    elif app == "slurm-multipass-localhost":
        from vantage_cli.apps.slurm_multipass_localhost.app import remove

        await remove(ctx, cluster_data)
    elif app == "slurm-microk8s-localhost":
        from vantage_cli.apps.slurm_microk8s_localhost.app import (
            cleanup_microk8s_localhost,
        )

        await cleanup_microk8s_localhost(ctx, cluster_data)
    else:
        raise ValueError(f"Unknown app type: {app}")


async def _cleanup_single_deployment(
    ctx: typer.Context,
    deployment_id: str,
    deployment: dict[str, Any],
    app: str,
    json_output: bool,
    console: Console,
) -> bool:
    """Clean up a single deployment and return True if successful."""
    try:
        # Get cluster data for cleanup functions
        cluster_data = deployment.get("cluster_data", {})

        # Call the appropriate cleanup function
        try:
            await _call_app_cleanup_function(ctx, app, cluster_data)
        except ValueError:
            logger.warning(f"Unknown app type '{app}', skipping cleanup")
            return False

        # Remove deployment entry from tracking file
        if remove_deployment(deployment_id, console):
            logger.debug(f"Cleaned up deployment '{deployment_id}'")
            return True
        else:
            logger.warning(f"Could not remove deployment '{deployment_id}' from tracking")
            return False

    except Exception as e:
        logger.warning(f"Cleanup of deployment '{deployment_id}' failed: {e}")
        return False


async def _cleanup_app_deployments(
    ctx: typer.Context, cluster_name: str, app: str, json_output: bool, console: Console
) -> dict[str, Any]:
    """Clean up all deployments of a specific app type for a cluster.

    Args:
        ctx: The typer context object for console access.
        cluster_name: Name of the cluster to clean up
        app: Type of app to clean up
        json_output: Whether to output JSON or rich console messages
        console: Console instance for output
        
    Returns:
        Dictionary with cleanup results
    """
    # Find deployments for this cluster
    cluster_deployments = list_deployments_by_cluster(cluster_name, console)

    # Filter to only the specified app type
    app_deployments = {
        dep_id: dep_data
        for dep_id, dep_data in cluster_deployments.items()
        if dep_data.get("app_name") == app
    }

    if not app_deployments:
        return {
            "deployments_found": 0,
            "deployments_cleaned": 0,
            "message": f"No '{app}' deployments found"
        }

    cleanup_count = 0
    failed_deployments = []
    for deployment_id, deployment in app_deployments.items():
        if await _cleanup_single_deployment(
            ctx, deployment_id, deployment, app, json_output, console
        ):
            cleanup_count += 1
        else:
            failed_deployments.append(deployment_id)

    return {
        "deployments_found": len(app_deployments),
        "deployments_cleaned": cleanup_count,
        "failed_deployments": failed_deployments,
        "message": f"Cleaned up {cleanup_count}/{len(app_deployments)} deployments"
    }
