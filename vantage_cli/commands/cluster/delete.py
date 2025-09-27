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

import logging
from typing import Optional

import typer
from typing_extensions import Annotated

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.sdk.cluster.crud import cluster_sdk
from vantage_cli.sdk.deployment.crud import deployment_sdk
from vantage_cli.sdk.deployment.schema import Deployment

logger = logging.getLogger(__name__)


async def _handle_orphaned_deployments(
    ctx: typer.Context,
    cluster_name: str,
    deployments: list[Deployment],
    app: Optional[str],
    json_output: bool,
) -> None:
    """Handle orphaned deployments when cluster doesn't exist."""
    if not json_output:
        ctx.obj.console.print(
            f"\n[yellow]⚠️  Found {len(deployments)} deployment(s) for cluster '{cluster_name}'[/yellow]"
        )
        ctx.obj.console.print("[yellow]These are orphaned (cluster no longer exists).[/yellow]")

    if app:
        # User specified an app, clean up that specific deployment
        deployment = next((d for d in deployments if d.app_name == app), None)
        if deployment:
            if not json_output:
                ctx.obj.console.print(
                    f"\n[blue]Cleaning up orphaned deployment for '{app}'...[/blue]"
                )
            cleanup_result = await _cleanup_single_deployment(ctx, cluster_name, app)

            output_data = {
                "cluster_name": cluster_name,
                "cluster_existed": False,
                "deployment_cleaned": cleanup_result,
                "message": f"Orphaned deployment for '{app}' cleaned up",
            }
            ctx.obj.formatter.render_delete(
                resource_name="Orphaned Deployment",
                resource_id=cluster_name,
                data=output_data,
            )
            return
        else:
            raise Abort(
                f"No deployment found for app '{app}' in orphaned deployments.",
                subject="Deployment Not Found",
                log_message=f"App '{app}' not found in orphaned deployments",
            )
    else:
        # No app specified, suggest using cleanup-orphans
        if not json_output:
            ctx.obj.console.print(
                "\n[dim]Use 'vantage app deployment cleanup-orphans' to clean up all orphaned deployments.[/dim]"
            )
            ctx.obj.console.print(
                "[dim]Or specify --app to clean up a specific deployment.[/dim]"
            )
        raise Abort(
            f"Cluster '{cluster_name}' not found, but {len(deployments)} orphaned deployment(s) exist.",
            subject="Orphaned Deployments Found",
            log_message="Cluster not found but has orphaned deployments",
            hint="Use 'vantage app deployment cleanup-orphans' to clean them up.",
        )


async def _handle_nonexistent_cluster(
    ctx: typer.Context,
    cluster_name: str,
    app: Optional[str],
    json_output: bool,
    verbose: bool,
) -> None:
    """Handle case when cluster doesn't exist - check for orphaned deployments."""
    if verbose and not json_output:
        ctx.obj.console.print(f"[yellow]Cluster '{cluster_name}' not found in API.[/yellow]")

    # Check for orphaned deployments
    deployments = await deployment_sdk.get_deployments_by_cluster(ctx, cluster_name)

    if deployments:
        await _handle_orphaned_deployments(ctx, cluster_name, deployments, app, json_output)
    else:
        # No cluster, no deployments
        raise Abort(
            f"No cluster found with name '{cluster_name}'.",
            subject="Cluster Not Found",
            log_message=f"Cluster '{cluster_name}' not found",
        )



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
            help="Cleanup the specified app deployment (e.g., slurm-lxd, slurm-multipass, slurm-microk8s)",
        ),
    ] = None,
):
    """Delete a Vantage cluster and optionally cleanup associated app deployments."""
    # Get JSON flag from context (automatically set by AsyncTyper)
    json_output = getattr(ctx.obj, "json_output", False)
    verbose = getattr(ctx.obj, "verbose", False)

    # Use UniversalOutputFormatter for consistent output

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

    try:
        if verbose and not json_output:
            ctx.obj.console.print(f"[bold blue]Querying cluster '{cluster_name}'...[/bold blue]")

        cluster = await cluster_sdk.get_cluster_by_name(ctx=ctx, cluster_name=cluster_name)

        # If cluster doesn't exist, check for orphaned deployments
        if not cluster:
            await _handle_nonexistent_cluster(ctx, cluster_name, app, json_output, verbose)
            return

        if verbose and not json_output:
            ctx.obj.console.print(f"[bold blue]Deleting cluster '{cluster_name}'...[/bold blue]")

        # Use SDK to delete cluster
        success = await cluster_sdk.delete_cluster(ctx, cluster_name)

        if not success:
            ctx.obj.formatter.render_error(
                error_message=f"Failed to delete cluster '{cluster_name}'."
            )
            raise Abort(
                f"Failed to delete cluster '{cluster_name}'.",
                subject="Deletion Failed",
                log_message="Cluster deletion failed",
            )

        cleanup_result = None
        if app:
            if verbose:
                ctx.obj.console.print(f"[bold blue]Cleaning up {app} deployments...[/bold blue]")

            cleanup_result = await _cleanup_single_deployment(ctx, cluster_name, app)

        # Output results
        output_data = {
            "cluster_name": cluster_name,
            "success": success,
            "message": f"Cluster '{cluster_name}' deleted successfully",
        }
        if app and cleanup_result is not None:
            output_data["app_cleanup"] = cleanup_result

        ctx.obj.formatter.render_delete(
            resource_name="Cluster",
            resource_id=cluster_name,
            data=output_data,
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


async def _call_app_remove_function(ctx: typer.Context, deployment: Deployment) -> None:
    """Call the appropriate remove function from the app module.

    Args:
        ctx: The typer context object
        deployment: The deployment object to remove

    Raises:
        ValueError: If the app is not found or doesn't have a remove function
    """
    # Import SDK here to avoid module-level initialization
    from vantage_cli.sdk.deployment_app import deployment_app_sdk

    available_apps_list = deployment_app_sdk.list()
    available_apps = {app.name: app for app in available_apps_list}

    if deployment.app_name not in available_apps:
        raise ValueError(f"App '{deployment.app_name}' not found")

    app = available_apps[deployment.app_name]

    # Check if the app module has a remove function
    if app.module and hasattr(app.module, "remove"):
        remove_function = getattr(app.module, "remove")
        await remove_function(ctx, deployment)
    else:
        raise ValueError(f"App '{deployment.app_name}' does not have a 'remove' function")


async def _cleanup_single_deployment(
    ctx: typer.Context,
    cluster_name: str,
    app_name: str,
) -> bool:
    """Clean up a single deployment and return True if successful.

    Args:
        ctx: The typer context object
        cluster_name: Name of the cluster
        app_name: Name of the app (e.g., 'slurm-multipass')

    Returns:
        True if cleanup was successful, False otherwise
    """
    deployments = await deployment_sdk.get_deployments_by_cluster(ctx, cluster_name)
    deployment = next((d for d in deployments if d.app_name == app_name), None)

    if not deployment:
        logger.warning(f"No deployment found for app '{app_name}' in cluster '{cluster_name}'")
        return False

    try:
        # Call the app's remove function
        await _call_app_remove_function(ctx, deployment)

        # Remove deployment entry from tracking file
        deleted = await deployment_sdk.delete(deployment.id)
        if deleted:
            logger.debug(f"Cleaned up deployment '{deployment.id}'")
            return True
        else:
            logger.warning(f"Could not remove deployment '{deployment.id}' from tracking")
            return False

    except ValueError as e:
        logger.warning(f"App error for '{app_name}': {e}")
        return False
    except Exception as e:
        logger.warning(f"Cleanup of deployment '{deployment.id}' failed: {e}")
        return False
