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
"""Delete a deployment and clean up associated resources."""

import typer
from typing_extensions import Annotated

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.sdk.deployment.crud import deployment_sdk


@attach_settings
@handle_abort
async def delete_deployment(
    ctx: typer.Context,
    deployment_id: Annotated[str, typer.Argument(help="ID or name of the deployment to delete")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation prompt")] = False,
) -> None:
    """Delete a deployment and clean up associated resources (multipass instances, etc)."""
    try:
        # Try to get deployment by ID first
        deployment = await deployment_sdk.get_deployment(ctx, deployment_id)

        if deployment is None:
            # Try searching by deployment name
            deployments = await deployment_sdk.list(ctx)
            for dep in deployments:
                if dep.name == deployment_id:
                    deployment = dep
                    break

            if deployment is None:
                raise Abort(
                    f"Deployment '{deployment_id}' not found.",
                    subject="Deployment Not Found",
                    log_message=f"Deployment not found: {deployment_id}",
                    hint="Use 'vantage app deployment list' to see available deployments.",
                )

        # Confirmation prompt unless force is used
        json_output = getattr(ctx.obj, "json_output", False)
        if not force and not json_output:
            from rich.prompt import Confirm

            ctx.obj.console.print(
                f"\n[yellow]⚠️  You are about to delete deployment '[bold red]{deployment.name}[/bold red]'[/yellow]"
            )
            ctx.obj.console.print(
                f"[yellow]App: {deployment.app_name}, Cluster: {deployment.cluster.name}[/yellow]"
            )
            ctx.obj.console.print("[yellow]This will clean up all associated resources![/yellow]")

            if not Confirm.ask("Are you sure you want to proceed?"):
                ctx.obj.console.print("[dim]Deletion cancelled.[/dim]")
                return

        # Get the app's remove function
        # Import SDK here to avoid module-level initialization
        from vantage_cli.sdk.deployment_app import deployment_app_sdk

        available_apps_list = deployment_app_sdk.list()
        available_apps = {app.name: app for app in available_apps_list}

        app_name = deployment.app_name

        cleanup_success = False
        cleanup_error = None

        # Try to call the app's remove function to clean up resources
        if app_name in available_apps:
            app = available_apps[app_name]

            if app.module and hasattr(app.module, "remove"):
                try:
                    remove_function = getattr(app.module, "remove")
                    await remove_function(ctx, deployment)
                    cleanup_success = True
                except Exception as e:
                    cleanup_error = str(e)
                    # Continue to delete deployment even if cleanup fails
            else:
                # No remove function - just delete the deployment record
                cleanup_error = f"App '{app_name}' does not have a remove function"
        else:
            cleanup_error = f"App '{app_name}' not found in available apps"

        # Delete the deployment from tracking
        # Always delete the deployment record, regardless of cleanup success
        deleted = await deployment_sdk.delete(deployment.id)
        if not deleted:
            raise Abort(
                f"Failed to delete deployment '{deployment.id}' from tracking.",
                subject="Deletion Failed",
                log_message="Deployment deletion failed",
            )

        # Output results
        output_data = {
            "deployment_id": deployment.id,
            "deployment_name": deployment.name,
            "app_name": deployment.app_name,
            "cluster_name": deployment.cluster.name,
            "success": True,
            "cleanup_success": cleanup_success,
        }

        if cleanup_error:
            output_data["cleanup_warning"] = cleanup_error

        ctx.obj.formatter.render_delete(
            resource_name="Deployment",
            resource_id=deployment.name,
            data=output_data,
        )

        if cleanup_error and not json_output:
            ctx.obj.console.print(f"\n[yellow]⚠️  Warning: {cleanup_error}[/yellow]")
            ctx.obj.console.print(
                "[yellow]Deployment record deleted, but manual cleanup may be required.[/yellow]"
            )

    except Abort:
        raise
    except Exception as e:
        raise Abort(
            f"Failed to delete deployment: {e}",
            subject="Delete Deployment Error",
            log_message=f"Deployment delete error: {e}",
        )
