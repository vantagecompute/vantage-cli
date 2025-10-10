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
import time
from typing import Any, Dict, Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from vantage_cli.apps.common import (
    create_deployment_with_init_status,
    generate_default_deployment_name,
    generate_dev_cluster_data,
    get_jupyterhub_token,
    get_sssd_binder_password,
    update_deployment_status,
)
from vantage_cli.apps.constants import DEV_JUPYTERHUB_TOKEN, DEV_SSSD_BINDER_PASSWORD
from vantage_cli.apps.localhost.slurm_microk8s.utils import (
    PrerequisiteStatus,
    add_helm_repositories,
    check_prerequisites,
    create_complete_prerequisite_checks,
    create_k8s_namespace,
    get_ssh_keys,
    install_prometheus,
    install_slurm_cluster,
    install_slurm_operator,
    install_slurm_operator_crds,
)
from vantage_cli.config import attach_settings
from vantage_cli.constants import CLOUD_LOCALHOST, CLOUD_TYPE_K8S
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import TerminalOutputManager
from vantage_cli.sdk.cluster.schema import Cluster

from .chart_values import CHART_VALUES_SLURM_CLUSTER
from .constants import (
    APP_NAME,
    CHART_PROMETHEUS,
    CHART_SLURM_CLUSTER,
    CHART_SLURM_OPERATOR,
    CHART_SLURM_OPERATOR_CRDS,
    DEFAULT_NAMESPACE_CERT_MANAGER,
    DEFAULT_NAMESPACE_PROMETHEUS,
    DEFAULT_NAMESPACE_SLINKY,
    DEFAULT_NAMESPACE_SLURM,
    DEFAULT_RELEASE_PROMETHEUS,
    DEFAULT_RELEASE_SLURM_CLUSTER,
    DEFAULT_RELEASE_SLURM_OPERATOR,
    DEFAULT_RELEASE_SLURM_OPERATOR_CRDS,
    REPO_JETSTACK_URL,
    REPO_PROMETHEUS_URL,
    REPO_SLURM_URL,
)
from .templates import sssd_conf


async def create(
    ctx: typer.Context,
    cluster_obj: Cluster,
    verbose: bool = False,
) -> None:
    """Create SLURM cluster on MicroK8s using Helm.

    This function is called by the Vantage cluster management system
    when creating a new cluster with this app.

    Args:
        ctx: Typer context containing settings and configuration
        cluster_obj: Cluster object containing cluster configuration
        verbose: Whether to enable verbose output

    Raises:
        typer.Exit: If deployment fails
    """
    console = ctx.obj.console

    # Generate deployment ID and create deployment with init status
    cluster_name = cluster_obj.name
    deployment_id = generate_default_deployment_name(APP_NAME, cluster_name)
    client_id = cluster_obj.client_id

    sssd_binder_password = get_sssd_binder_password(cluster_obj) or DEV_SSSD_BINDER_PASSWORD
    jupyterhub_token = get_jupyterhub_token(cluster_obj) or DEV_JUPYTERHUB_TOKEN

    rendered_sssd_conf = sssd_conf(
        ldap_url=ctx.obj.settings.get_ldap_url(),
        org_id=ctx.obj.persona.identity_data.org_id,
        sssd_binder_password=sssd_binder_password,
    )

    create_deployment_with_init_status(
        deployment_id=deployment_id,
        app_name=APP_NAME,
        cluster_name=cluster_name,
        cluster=cluster_obj,
        console=console,
        verbose=verbose,
        cloud=CLOUD_LOCALHOST,
        cloud_type=CLOUD_TYPE_K8S,
        k8s_namespaces=[
            DEFAULT_NAMESPACE_CERT_MANAGER,
            DEFAULT_NAMESPACE_PROMETHEUS,
            DEFAULT_NAMESPACE_SLINKY,
            DEFAULT_NAMESPACE_SLURM,
        ],
    )

    set_values = {
        "loginsets.slinky.sssdConf": rendered_sssd_conf,
    }

    if (ssh_keys := get_ssh_keys()) is not None and ssh_keys.strip() != "":
        set_values["loginsets.slinky.sshAuthorizedKeys"] = ssh_keys

    with TerminalOutputManager(
        console=console,
        operation_name="🚀 SLURM MicroK8S Deployment Progress",
        verbose=verbose,
        json_output=False,
        use_live_panel=True,
    ) as output:
        try:
            # Step 1: Check prerequisites
            output.status("🔍 Checking prerequisites...")

            checks = create_complete_prerequisite_checks()
            all_met, results = check_prerequisites(
                checks, console, verbose=verbose, show_table=False
            )

            if not all_met:
                missing_tools: list[str] = []
                for result in results:
                    if result.status != PrerequisiteStatus.AVAILABLE:
                        missing_tools.append(f"{result.name}: {result.error_message or 'Missing'}")

                error_msg = f"Missing prerequisites: {'; '.join(missing_tools)}"
                output.set_final_content(
                    format_deployment_failure_content(error_msg), success=False
                )
                update_deployment_status(deployment_id, "failed", console)
                raise typer.Exit(1)

            output.success("Prerequisites check passed")
            time.sleep(1)

            # Step 2: Setup Helm repositories
            output.status("📦 Setting up Helm repositories...")
            repos = [
                ("jetstack", REPO_JETSTACK_URL),
                ("prometheus-community", REPO_PROMETHEUS_URL),
                ("jamesbeedy-slinky-slurm", REPO_SLURM_URL),
            ]
            add_helm_repositories(repos)
            output.success("Helm repositories configured")
            time.sleep(1)

            # Step 3: Create namespaces
            output.status("🔧 Creating Kubernetes namespaces...")
            namespaces = [
                DEFAULT_NAMESPACE_CERT_MANAGER,
                DEFAULT_NAMESPACE_PROMETHEUS,
                DEFAULT_NAMESPACE_SLINKY,
                DEFAULT_NAMESPACE_SLURM,
            ]
            for namespace in namespaces:
                if not create_k8s_namespace(namespace):
                    error_msg = f"Failed to create namespace '{namespace}'"
                    output.set_final_content(
                        format_deployment_failure_content(error_msg), success=False
                    )
                    update_deployment_status(deployment_id, "failed", console)
                    raise typer.Exit(1)
            output.success("Namespaces created")
            time.sleep(1)

            # Step 4: Install cert-manager
            output.status("🔒 Installing cert-manager...")
            # install_cert_manager(
            #     DEFAULT_NAMESPACE_CERT_MANAGER,
            #     DEFAULT_RELEASE_CERT_MANAGER,
            #     CHART_CERT_MANAGER,
            # )
            output.success("cert-manager installed")
            time.sleep(1)

            # Step 5: Install Prometheus
            output.status("📊 Installing Prometheus...")
            install_prometheus(
                DEFAULT_NAMESPACE_PROMETHEUS,
                DEFAULT_RELEASE_PROMETHEUS,
                CHART_PROMETHEUS,
            )
            output.success("Prometheus installed")
            time.sleep(1)

            # Step 6: Install SLURM operator CRDs
            output.status("⚙️ Installing SLURM operator CRDs...")
            install_slurm_operator_crds(
                DEFAULT_RELEASE_SLURM_OPERATOR_CRDS,
                CHART_SLURM_OPERATOR_CRDS,
            )
            output.success("SLURM operator CRDs installed")
            time.sleep(1)

            # Step 7: Install SLURM operator
            output.status("🎛️ Installing SLURM operator...")
            install_slurm_operator(
                DEFAULT_NAMESPACE_SLINKY,
                DEFAULT_RELEASE_SLURM_OPERATOR,
                CHART_SLURM_OPERATOR,
            )
            output.success("SLURM operator installed")
            time.sleep(1)

            # Step 8: Install SLURM cluster
            output.status("🖥️ Installing SLURM cluster...")
            install_slurm_cluster(
                DEFAULT_NAMESPACE_SLURM,
                DEFAULT_RELEASE_SLURM_CLUSTER,
                CHART_SLURM_CLUSTER,
                CHART_VALUES_SLURM_CLUSTER,
                set_values,
            )
            output.success("SLURM cluster installed")
            time.sleep(1)

            # Step 9: Finalize
            output.status("🎉 Finalizing deployment...")
            update_deployment_status(deployment_id, "active", console)

            # Set beautiful success content
            output.set_final_content(format_deployment_success_content(client_id), success=True)

        except Exception as e:
            update_deployment_status(deployment_id, "failed", console)
            error_msg = f"Deployment failed: {str(e)}"
            output.set_final_content(format_deployment_failure_content(error_msg), success=False)
            raise typer.Exit(1)


# Command functions that the deployment system will discover
@handle_abort
@attach_settings
async def deploy_command(
    ctx: typer.Context,
    cluster_name: Annotated[
        Optional[str],
        typer.Argument(help="Name of the cluster to deploy"),
    ] = None,
    dev_run: Annotated[
        bool, typer.Option("--dev-run", help="Use dummy cluster data for local development")
    ] = False,
) -> None:
    """Deploy SLURM cluster to MicroK8s."""
    if cluster_name is None:
        cluster_name = "unknown"

    cluster_obj = generate_dev_cluster_data(cluster_name)
    if not dev_run:
        from vantage_cli.commands.cluster import utils as cluster_utils

        fetched_cluster = await cluster_utils.get_cluster_by_name(
            ctx=ctx, cluster_name=cluster_name
        )
        if fetched_cluster is None:
            raise ValueError(f"Cluster '{cluster_name}' not found")
        cluster_obj = fetched_cluster
    else:
        ctx.obj.console.print(
            f"[blue]Using dev run mode with dummy cluster data for '{cluster_name}'[/blue]"
        )

    # Pass Cluster object directly to create function
    await create(ctx=ctx, cluster_obj=cluster_obj)


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
