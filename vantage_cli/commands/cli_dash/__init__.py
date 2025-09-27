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
"""Vantage `cli-dash` command for the Vantage CLI.

This command provides an interactive terminal dashboard for managing and monitoring
Vantage resources using the SDK.

SDK Integration:
---------------
The dashboard uses the following SDK modules:
- `vantage_cli.sdk.cluster` - For fetching and managing clusters
- `vantage_cli.sdk.deployment` - For fetching and managing deployments
- `vantage_cli.sdk.profile` - For managing authentication profiles

The command automatically:
1. Fetches clusters using `cluster_sdk.list_clusters()`
2. Fetches deployments using `deployment_sdk.list()`
3. Converts SDK objects to dashboard ServiceConfig using `ServiceConfig.from_cluster()`
   and `ServiceConfig.from_deployment()`
4. Creates the dashboard using `DashboardApp.from_sdk_data()` factory method

Example Usage:
-------------
```bash
uv run vantage cli-dash
```

This will launch the interactive dashboard with all your clusters and deployments.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Iterable, List, TypeVar, cast

import typer

from vantage_cli.config import attach_settings
from vantage_cli.dashboard import DashboardApp, DashboardConfig
from vantage_cli.exceptions import Abort
from vantage_cli.exceptions import (
    handle_abort as _handle_abort,  # pyright: ignore[reportUnknownVariableType]
)
from vantage_cli.sdk.cluster import cluster_sdk
from vantage_cli.sdk.cluster.schema import Cluster
from vantage_cli.sdk.deployment import deployment_sdk
from vantage_cli.sdk.deployment.schema import Deployment
from vantage_cli.sdk.deployment_app import deployment_app_sdk
from vantage_cli.sdk.deployment_app.schema import DeploymentApp

logger = logging.getLogger(__name__)


F = TypeVar("F", bound=Callable[..., Any])


def handle_abort(func: F) -> F:
    """Handle abort decorator with proper type casting.

    Args:
        func: The function to wrap with abort handling

    Returns:
        The wrapped function with type preservation
    """
    return cast(F, _handle_abort(func))


def _cluster_handler(cluster: Cluster):  # pragma: no cover - trivial closure
    """Create a worker handler for a cluster.

    This handler returns cluster status information when the worker is executed.
    """

    def handler(worker_id: str) -> Dict[str, str]:
        return {
            "worker": worker_id,
            "status": cluster.status,
            "provider": cluster.cluster_type,
            "owner": cluster.owner_email,
            "ready": "yes" if cluster.is_ready else "no",
        }

    return handler


def _deployment_handler(deployment: Deployment):  # pragma: no cover - trivial closure
    """Create a worker handler for a deployment.

    This handler returns deployment status information when the worker is executed.
    """

    def handler(worker_id: str) -> Dict[str, str]:
        return {
            "worker": worker_id,
            "status": deployment.status,
            "cluster": deployment.cluster.name,
            "cloud": deployment.cloud.name,
            "substrate": deployment.substrate,
        }

    return handler


def _build_custom_handlers(
    clusters: Iterable[Cluster], deployments: Iterable[Deployment]
) -> Dict[str, Callable[[str], Dict[str, str]]]:
    """Build custom worker handlers for clusters and deployments.

    These handlers are called when workers are executed to gather status information.
    """
    handlers: Dict[str, Callable[[str], Dict[str, str]]] = {}

    for cluster in clusters:
        handlers[cluster.name] = _cluster_handler(cluster)

    for deployment in deployments:
        handlers[deployment.name] = _deployment_handler(deployment)

    return handlers


def _build_platform_info(
    ctx: typer.Context,
    cluster_count: int,
    deployment_count: int,
) -> Dict[str, str]:
    settings = getattr(ctx.obj, "settings", None)

    if settings is None:
        return {
            "name": "Vantage Compute",
            "cluster_url": "https://app.vantagecompute.ai/clusters",
            "notebooks_url": "https://app.vantagecompute.ai/notebooks",
            "docs_url": "https://docs.vantagecompute.ai/platform/deployment-applications",
            "support_email": "support@vantagecompute.ai",
            "summary": f"{cluster_count} cluster(s) · {deployment_count} deployment(s)",
        }

    return {
        "name": "Vantage Compute",
        "cluster_url": f"{settings.vantage_url}/clusters",
        "notebooks_url": f"{settings.vantage_url}/notebooks",
        "docs_url": "https://docs.vantagecompute.ai/platform/deployment-applications",
        "support_email": "support@vantagecompute.ai",
        "summary": f"{cluster_count} cluster(s) · {deployment_count} deployment(s)",
    }


@handle_abort
@attach_settings
async def cli_dash(
    ctx: typer.Context,
) -> None:
    """Vantage CLI Dashboard - Interactive terminal dashboard.

    This command creates an interactive dashboard using the Vantage SDK to display
    and manage clusters, deployments, and profiles. The dashboard automatically
    fetches data using the SDK and provides real-time monitoring and management.
    """
    clusters: List[Cluster] = []
    deployments: List[Deployment] = []
    apps: List[DeploymentApp] = []

    try:
        clusters = await cluster_sdk.list_clusters(ctx)
    except Abort as exc:
        logger.warning("Unable to load clusters: %s", exc.message)
        typer.echo(f"⚠️ Unable to load clusters from the API: {exc.message}")
    except Exception as exc:  # pragma: no cover - defensive branch
        logger.exception("Unexpected error loading clusters")
        typer.echo(f"⚠️ Unexpected error loading clusters: {exc}")

    try:
        deployments = await deployment_sdk.list(ctx)
    except Abort as exc:
        logger.warning("Unable to load deployments: %s", exc.message)
        typer.echo(f"⚠️ Unable to load deployments: {exc.message}")
    except Exception as exc:  # pragma: no cover - defensive branch
        logger.exception("Unexpected error loading deployments")
        typer.echo(f"⚠️ Unexpected error loading deployments: {exc}")

    # Load deployment apps using the SDK
    try:
        apps = deployment_app_sdk.list()
        logger.debug(f"Loaded {len(apps)} deployment apps")
    except Exception as exc:  # pragma: no cover - defensive branch
        logger.exception("Unexpected error loading deployment apps")
        typer.echo(f"⚠️ Unexpected error loading deployment apps: {exc}")

    # Build custom handlers for worker execution
    custom_handlers = _build_custom_handlers(clusters, deployments)

    subtitle = (
        f"Interactive view of {len(clusters)} cluster(s) and {len(deployments)} deployment(s)"
    )

    config = DashboardConfig(
        title="Vantage CLI Dashboard",
        subtitle=subtitle,
        enable_stats=True,
        enable_logs=True,
        enable_controls=True,
        enable_clusters=True,
        refresh_interval=0.5,
    )

    platform_info = _build_platform_info(ctx, len(clusters), len(deployments))

    typer.echo(f"🚀 Launching {config.title}...")

    # Use the new from_sdk_data factory method to create the dashboard
    app_instance = DashboardApp.from_sdk_data(
        clusters=clusters,
        deployments=deployments,
        apps=apps,
        config=config,
        custom_handlers=custom_handlers or None,
        platform_info=platform_info,
        ctx=ctx,
    )

    try:
        typer.echo("💡 Use Ctrl+C to quit, or 'q' inside the app")
        await app_instance.run_async()
    except KeyboardInterrupt:
        typer.echo("\n👋 Dashboard interrupted by user")
    except Exception as e:  # pragma: no cover - passthrough
        typer.echo(f"\n💥 Dashboard error: {e}")
        raise typer.Exit(1)
