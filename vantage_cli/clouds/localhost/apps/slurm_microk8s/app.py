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
"""MicroK8s application support for deploying the Slurm Operator & Slurm cluster."""

import subprocess
from copy import deepcopy
from typing import Any, Dict, Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from vantage_cli.clouds.common import (
    create_deployment_with_init_status,
    generate_dev_cluster_data,
)
from vantage_cli.clouds.constants import DEV_JUPYTERHUB_TOKEN, DEV_ORG_ID, DEV_SSSD_BINDER_PASSWORD
from vantage_cli.clouds.localhost.apps.slurm_microk8s.chart_values import (
    CHART_VALUES_SLURM_CLUSTER,
)
from vantage_cli.clouds.localhost.apps.slurm_microk8s.constants import (
    APP_NAME,
    DEFAULT_NAMESPACE_CERT_MANAGER,
    DEFAULT_NAMESPACE_PROMETHEUS,
    DEFAULT_NAMESPACE_SLINKY,
    DEFAULT_NAMESPACE_SLURM,
    SUBSTRATE,
)
from vantage_cli.clouds.localhost.apps.slurm_microk8s.render import show_getting_started_help
from vantage_cli.clouds.localhost.apps.slurm_microk8s.templates import sssd_conf
from vantage_cli.clouds.localhost.apps.slurm_microk8s.utils import (
    deploy_microk8s_stack,
    get_ssh_keys,
)
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.sdk.admin.management.organizations import get_extra_attributes
from vantage_cli.sdk.cluster.crud import cluster_sdk
from vantage_cli.sdk.cluster.schema import Cluster, VantageClusterContext


async def create(ctx: typer.Context, cluster: Cluster) -> typer.Exit:
    """Deploy a SLURM cluster on MicroK8s for the provided cluster definition."""
    console = getattr(ctx.obj, "console", Console())
    formatter = getattr(ctx.obj, "formatter", None)
    verbose = bool(getattr(ctx.obj, "verbose", False))
    settings = getattr(ctx.obj, "settings", None)

    if settings is None:
        console.print("[bold red]Error:[/bold red] CLI settings are not available.")
        return typer.Exit(code=1)

    def render_error(message: str) -> None:
        if formatter is not None:
            formatter.render_error(message)
        else:
            console.print(f"[bold red]Error:[/bold red] {message}")

    client_secret = cluster.client_secret
    if not client_secret:
        render_error("Cluster is missing client secret. Please debug.")
        return typer.Exit(code=1)

    sssd_binder_password = cluster.sssd_binder_password or DEV_SSSD_BINDER_PASSWORD
    if not sssd_binder_password:
        render_error("Cluster is missing SSSD binder password. Please debug.")
        return typer.Exit(code=1)

    jupyterhub_token = (
        cluster.creation_parameters.get("jupyterhub_token")
        if cluster.creation_parameters
        else None
    ) or DEV_JUPYTERHUB_TOKEN

    persona = getattr(ctx.obj, "persona", None)
    persona_org_id = None
    if persona is not None:
        identity_data = getattr(persona, "identity_data", None)
        persona_org_id = getattr(identity_data, "org_id", None)

    org_id = (
        (cluster.creation_parameters.get("org_id") if cluster.creation_parameters else None)
        or persona_org_id
        or DEV_ORG_ID
    )

    ssh_keys = get_ssh_keys() or ""

    vantage_cluster_ctx = VantageClusterContext(
        cluster_name=cluster.name,
        client_id=cluster.client_id,
        client_secret=client_secret,
        base_api_url=settings.get_apis_url(),
        oidc_base_url=settings.get_auth_url(),
        oidc_domain=settings.oidc_domain,
        tunnel_api_url=settings.get_tunnel_url(),
        jupyterhub_token=jupyterhub_token,
        sssd_binder_password=sssd_binder_password,
        ldap_url=settings.get_ldap_url(),
        org_id=org_id,
    )

    from vantage_cli.sdk.cloud.crud import cloud_sdk

    cloud = cloud_sdk.get("localhost")
    if cloud is None:
        console.print("[bold red]Error:[/bold red] Cloud 'localhost' not found. Please debug")
        return typer.Exit(code=1)

    deployment = create_deployment_with_init_status(
        app_name=APP_NAME,
        cluster=cluster,
        vantage_cluster_ctx=vantage_cluster_ctx,
        cloud=cloud,
        substrate=SUBSTRATE,
        additional_metadata={
            "org_id": org_id,
            "ssh_keys_present": bool(ssh_keys),
        },
        k8s_namespaces=[
            DEFAULT_NAMESPACE_SLURM,
            DEFAULT_NAMESPACE_SLINKY,
            DEFAULT_NAMESPACE_PROMETHEUS,
            DEFAULT_NAMESPACE_CERT_MANAGER,
        ],
        verbose=verbose,
    )
    deployment.write()

    chart_values = deepcopy(CHART_VALUES_SLURM_CLUSTER)
    chart_values["clusterName"] = cluster.client_id
    loginset_values = chart_values["loginsets"]["slinky"]
    loginset_values["rootSshAuthorizedKeys"] = ssh_keys
    loginset_values["sssdConf"] = sssd_conf(settings.get_ldap_url(), org_id, sssd_binder_password)

    set_values: Dict[str, str] = {
        "clusterName": cluster.client_id,
    }

    try:
        deploy_microk8s_stack(
            console=console,
            verbose=verbose,
            set_values=set_values,
            chart_values=chart_values,
        )
    except Exception as exc:  # noqa: BLE001 - propagate deployment failure context
        deployment.status = "error"
        deployment.write()
        render_error(f"Deployment failed: {exc}")
        return typer.Exit(code=1)

    deployment.status = "active"
    deployment.write()

    success_message = (
        f"SLURM MicroK8s deployment '{deployment.name}' created for client '{cluster.client_id}'."
    )

    if formatter is not None:
        if getattr(formatter, "json_output", False):
            formatter.output(
                {
                    "message": success_message,
                    "deployment": deployment.model_dump(mode="json"),
                },
                title="Deployment Result",
            )
        else:
            formatter.success(success_message)
    else:
        console.print(f"[bold green]{success_message}[/bold green]")

    if not (formatter is not None and getattr(formatter, "json_output", False)):
        show_getting_started_help(console)

    return typer.Exit(code=0)


# Command functions that the deployment system will discover
@handle_abort
@attach_settings
async def create_command(
    ctx: typer.Context,
    cluster_name: Annotated[
        str,
        typer.Argument(help="Name of the cluster to deploy"),
    ],
    dev_run: Annotated[
        bool, typer.Option("--dev-run", help="Use dummy cluster data for local development")
    ] = False,
) -> None | typer.Exit:
    """Create a SLURM cluster on MicroK8s."""
    cluster = generate_dev_cluster_data(cluster_name)

    if not dev_run:
        fetched_cluster = await cluster_sdk.get_cluster_by_name(ctx, cluster_name)
        if fetched_cluster is None:
            raise typer.Exit(code=1)

        cluster = fetched_cluster

        if (extra_attrs := await get_extra_attributes(ctx)) is not None:
            if sssd_binder_password := extra_attrs.get("sssd_binder_password"):
                cluster.sssd_binder_password = sssd_binder_password
    else:
        ctx.obj.console.print(
            f"[blue]Using dev run mode with dummy cluster data for '{cluster_name}'[/blue]"
        )

    await create(ctx=ctx, cluster=cluster)


@handle_abort
@attach_settings
async def status_command(
    ctx: typer.Context,
) -> None:
    """Check SLURM deployment status."""
    console = ctx.obj.console if hasattr(ctx.obj, "console") else Console()

    try:
        namespaces = [
            DEFAULT_NAMESPACE_SLURM,
            DEFAULT_NAMESPACE_SLINKY,
            DEFAULT_NAMESPACE_PROMETHEUS,
            DEFAULT_NAMESPACE_CERT_MANAGER,
        ]

        for namespace in namespaces:
            console.print(f"[cyan]Checking namespace: {namespace}[/cyan]")
            result = subprocess.run(
                ["microk8s", "kubectl", "get", "pods", "-n", namespace],
                capture_output=True,
                text=True,
                check=True,
            )
            console.print(result.stdout)
            console.print()
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗[/red] Failed to get deployment status: {e}")
        raise typer.Exit(1)


@handle_abort
@attach_settings
async def remove_command(
    ctx: typer.Context,
    cluster_name: Annotated[
        Optional[str],
        typer.Argument(help="Name of the cluster to remove"),
    ] = None,
    force: Annotated[bool, typer.Option(help="Force removal without confirmation")] = False,
) -> None:
    """Remove SLURM deployment."""
    console = ctx.obj.console if hasattr(ctx.obj, "console") else Console()

    if cluster_name is None:
        cluster_name = "unknown"

    if not force:
        confirm = typer.confirm(
            f"Are you sure you want to remove SLURM deployment for '{cluster_name}'?"
        )
        if not confirm:
            console.print("Operation cancelled.")
            return

    try:
        namespaces = [
            DEFAULT_NAMESPACE_SLURM,
            DEFAULT_NAMESPACE_SLINKY,
            DEFAULT_NAMESPACE_PROMETHEUS,
            DEFAULT_NAMESPACE_CERT_MANAGER,
        ]

        for namespace in namespaces:
            try:
                subprocess.run(
                    [
                        "microk8s",
                        "kubectl",
                        "delete",
                        "namespace",
                        namespace,
                        "--ignore-not-found=true",
                    ],
                    capture_output=True,
                    check=True,
                )
                console.print(f"[green]✓[/green] Successfully removed namespace '{namespace}'")
            except subprocess.CalledProcessError:
                console.print(
                    f"[yellow]Warning:[/yellow] Namespace '{namespace}' not found or already removed"
                )

        console.print(
            f"[green]✓[/green] Successfully removed SLURM deployment for '{cluster_name}'"
        )
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to remove deployment: {e}")
        raise typer.Exit(1)


async def cleanup_microk8s_localhost(ctx: typer.Context, cluster_data: Dict[str, Any]) -> None:
    """Clean up a MicroK8s localhost deployment.

    Args:
        ctx: Typer context (unused but required for signature compatibility)
        cluster_data: Dictionary containing cluster information including 'cluster_name'
    """
    cluster_name = cluster_data.get("cluster_name")
    if not cluster_name:
        raise ValueError("cluster_name is required in cluster_data")

    # Use the existing remove_command function
    remove_command(cluster_name)
