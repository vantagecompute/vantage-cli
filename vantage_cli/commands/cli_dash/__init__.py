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
"""Vantage `cli-dash` command for the Vantage CLI."""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, TypeVar, cast

import typer
from loguru import logger

from vantage_cli.config import attach_settings
from vantage_cli.dashboard import DashboardApp, DashboardConfig, ServiceConfig
from vantage_cli.exceptions import Abort
from vantage_cli.exceptions import handle_abort as _handle_abort  # pyright: ignore[reportUnknownVariableType]
from vantage_cli.sdk.cluster import cluster_sdk
from vantage_cli.sdk.cluster.schema import Cluster
from vantage_cli.sdk.deployment import deployment_sdk
from vantage_cli.sdk.deployment.schema import Deployment

F = TypeVar("F", bound=Callable[..., Any])


def handle_abort(func: F) -> F:
    return cast(F, _handle_abort(func))


def _cluster_emoji(cluster: Cluster) -> str:
    """Return an emoji representing the cluster provider."""

    provider_map = {
        "aws": "☁️",
        "gcp": "☁️",
        "azure": "☁️",
        "localhost": "💻",
        "maas": "🛠️",
        "on_prem": "🏢",
    }
    return provider_map.get(cluster.provider.lower(), "🖥️")


def _deployment_emoji(deployment: Deployment) -> str:
    """Return an emoji representing the deployment substrate."""

    substrate_map = {
        "k8s": "🚢",
        "metal": "🔩",
        "vm": "🧱",
    }
    return substrate_map.get(deployment.substrate.lower(), "🚀")


def _cluster_handler(cluster: Cluster):  # pragma: no cover - trivial closure
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
    def handler(worker_id: str) -> Dict[str, str]:
        return {
            "worker": worker_id,
            "status": deployment.status,
            "cluster": deployment.cluster.name,
            "cloud": deployment.cloud_provider,
            "substrate": deployment.substrate,
        }

    return handler


def _build_cluster_services(clusters: Iterable[Cluster]) -> List[ServiceConfig]:
    return [
        ServiceConfig(
            name=cluster.name,
            url=cluster.jupyterhub_url,
            emoji=_cluster_emoji(cluster),
            dependencies=[],
        )
        for cluster in clusters
    ]


def _build_deployment_services(deployments: Iterable[Deployment]) -> List[ServiceConfig]:
    services: List[ServiceConfig] = []
    for deployment in deployments:
        dependencies: List[str] = []
        if deployment.cluster:
            dependencies.append(deployment.cluster.name)

        services.append(
            ServiceConfig(
                name=deployment.name,
                url=deployment.vantage_cluster_ctx.base_api_url,
                emoji=_deployment_emoji(deployment),
                dependencies=dependencies,
            )
        )

    return services


def _build_custom_handlers(
    clusters: Iterable[Cluster], deployments: Iterable[Deployment]
) -> Dict[str, Callable[[str], Dict[str, str]]]:
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
    """Vantage CLI Dashboard - Interactive terminal dashboard."""

    clusters: List[Cluster] = []
    deployments: List[Deployment] = []

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

    services = _build_cluster_services(clusters) + _build_deployment_services(deployments)
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

    app_instance = DashboardApp(
        config=config,
        services=services or None,
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
