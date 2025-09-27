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
"""Clean up orphaned deployments whose clusters no longer exist."""

import typer
from typing_extensions import Annotated

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.sdk.cluster.crud import cluster_sdk
from vantage_cli.sdk.deployment.crud import deployment_sdk
from vantage_cli.sdk.deployment.schema import Deployment


async def _find_orphaned_deployments(
    ctx: typer.Context, all_deployments: list[Deployment]
) -> list[Deployment]:
    """Find deployments whose clusters no longer exist."""
    orphaned = []
    cluster_cache = {}

    json_output = getattr(ctx.obj, "json_output", False)
    if not json_output:
        ctx.obj.console.print(f"[blue]Checking {len(all_deployments)} deployment(s)...[/blue]")

    for deployment in all_deployments:
        cluster_name = deployment.cluster.name

        if cluster_name not in cluster_cache:
            cluster = await cluster_sdk.get_cluster_by_name(ctx, cluster_name)
            cluster_cache[cluster_name] = cluster

        if cluster_cache[cluster_name] is None:
            orphaned.append(deployment)

    return orphaned


def _prepare_orphaned_data(orphaned: list[Deployment]) -> list[dict]:
    """Prepare orphaned deployment data for display."""
    return [
        {
            "id": deployment.id,
            "name": deployment.name,
            "app_name": deployment.app_name,
            "cluster_name": deployment.cluster.name,
            "status": deployment.status,
            "created_at": deployment.formatted_created_at,
        }
        for deployment in orphaned
    ]


def _confirm_cleanup(ctx: typer.Context, orphaned_data: list[dict]) -> bool:
    """Prompt user to confirm cleanup of orphaned deployments."""
    from rich.prompt import Confirm

    ctx.obj.console.print(
        f"\n[yellow]⚠️  Found {len(orphaned_data)} orphaned deployment(s):[/yellow]\n"
    )

    ctx.obj.formatter.render_list(
        data=orphaned_data,
        resource_name="Orphaned Deployments",
    )

    ctx.obj.console.print(
        "\n[yellow]These deployments reference clusters that no longer exist.[/yellow]"
    )
    ctx.obj.console.print(
        "[yellow]This will attempt to clean up all associated resources![/yellow]"
    )

    return Confirm.ask("\nAre you sure you want to clean up these deployments?")


async def _cleanup_single_deployment(
    ctx: typer.Context, deployment: Deployment, available_apps: dict
) -> dict[str, str | bool]:
    """Clean up a single orphaned deployment."""
    result: dict[str, str | bool] = {
        "deployment_id": deployment.id,
        "deployment_name": deployment.name,
        "cluster_name": deployment.cluster.name,
        "app_name": deployment.app_name,
    }

    try:
        app_name = deployment.app_name

        if app_name in available_apps:
            app_info = available_apps[app_name]

            if "module" in app_info and hasattr(app_info["module"], "remove"):
                remove_function = getattr(app_info["module"], "remove")
                await remove_function(ctx, deployment)
                result["status"] = "cleaned"
            else:
                await deployment_sdk.delete(deployment.id)
                result["status"] = "deleted (no cleanup function)"
        else:
            await deployment_sdk.delete(deployment.id)
            result["status"] = "deleted (app not found)"

        result["success"] = True

    except Exception as e:
        result["success"] = False
        result["status"] = "failed"
        result["error"] = str(e)

    return result


def _display_cleanup_results(ctx: typer.Context, cleanup_results: list[dict]) -> None:
    """Display cleanup results to the user."""
    json_output = getattr(ctx.obj, "json_output", False)
    success_count = sum(1 for r in cleanup_results if r["success"])
    failed_count = len(cleanup_results) - success_count

    if json_output:
        ctx.obj.formatter.render_list(
            data=cleanup_results,
            resource_name="Cleanup Results",
        )
    else:
        ctx.obj.console.print("\n[green]✓ Cleanup complete:[/green]")
        ctx.obj.console.print(f"  [green]• Cleaned: {success_count}[/green]")
        if failed_count > 0:
            ctx.obj.console.print(f"  [red]• Failed: {failed_count}[/red]")
            ctx.obj.console.print("\n[yellow]Failed deployments:[/yellow]")
            for result in cleanup_results:
                if not result["success"]:
                    ctx.obj.console.print(
                        f"  [red]• {result['deployment_name']}: {result.get('error', 'Unknown error')}[/red]"
                    )


@attach_settings
@handle_abort
async def cleanup_orphans(
    ctx: typer.Context,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be cleaned up without actually cleaning"),
    ] = False,
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation prompt")] = False,
) -> None:
    """Find and clean up deployments whose clusters no longer exist."""
    json_output = getattr(ctx.obj, "json_output", False)

    try:
        all_deployments = await deployment_sdk.list(ctx)

        if not all_deployments:
            if not json_output:
                ctx.obj.console.print("[green]✓ No deployments found.[/green]")
            else:
                ctx.obj.formatter.render_list(data=[], resource_name="Orphaned Deployments")
            return

        orphaned = await _find_orphaned_deployments(ctx, all_deployments)

        if not orphaned:
            if not json_output:
                ctx.obj.console.print("[green]✓ No orphaned deployments found.[/green]")
            else:
                ctx.obj.formatter.render_list(data=[], resource_name="Orphaned Deployments")
            return

        orphaned_data = _prepare_orphaned_data(orphaned)

        if dry_run:
            if not json_output:
                ctx.obj.console.print(
                    f"\n[yellow]🔍 Found {len(orphaned)} orphaned deployment(s) (DRY RUN):[/yellow]\n"
                )
            ctx.obj.formatter.render_list(
                data=orphaned_data, resource_name="Orphaned Deployments (Dry Run)"
            )
            if not json_output:
                ctx.obj.console.print(
                    "\n[dim]Run without --dry-run to clean up these deployments.[/dim]"
                )
            return

        if not force and not json_output:
            if not _confirm_cleanup(ctx, orphaned_data):
                ctx.obj.console.print("[dim]Cleanup cancelled.[/dim]")
                return

        from vantage_cli.sdk.deployment_app import deployment_app_sdk

        available_apps = deployment_app_sdk.list()
        cleanup_results = []

        for deployment in orphaned:
            result = await _cleanup_single_deployment(ctx, deployment, available_apps)
            cleanup_results.append(result)

        _display_cleanup_results(ctx, cleanup_results)

    except Abort:
        raise
    except Exception as e:
        raise Abort(
            f"Failed to clean up orphaned deployments: {e}",
            subject="Cleanup Error",
            log_message=f"Orphan cleanup error: {e}",
        )
