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
    update_deployment_status,
    validate_cluster_data,
)
from vantage_cli.apps.slurm_microk8s_localhost.constants import (
    APP_NAME,
    CHART_CERT_MANAGER,
    CHART_PROMETHEUS,
    CHART_SLURM_CLUSTER,
    CHART_SLURM_OPERATOR,
    CHART_SLURM_OPERATOR_CRDS,
    DEFAULT_NAMESPACE_CERT_MANAGER,
    DEFAULT_NAMESPACE_PROMETHEUS,
    DEFAULT_NAMESPACE_SLINKY,
    DEFAULT_NAMESPACE_SLURM,
    DEFAULT_RELEASE_CERT_MANAGER,
    DEFAULT_RELEASE_PROMETHEUS,
    DEFAULT_RELEASE_SLURM_CLUSTER,
    DEFAULT_RELEASE_SLURM_OPERATOR,
    DEFAULT_RELEASE_SLURM_OPERATOR_CRDS,
    REPO_JETSTACK_URL,
    REPO_PROMETHEUS_URL,
    REPO_SLURM_URL,
)
from vantage_cli.apps.slurm_microk8s_localhost.render import (
    format_deployment_failure_content,
    format_deployment_success_content,
)
from vantage_cli.apps.utils import (
    PrerequisiteStatus,
    check_prerequisites,
    create_complete_prerequisite_checks,
    create_k8s_namespace,
    helm_repo_add,
    helm_repo_update,
    microk8s_deploy_chart,
)
from vantage_cli.config import attach_settings
from vantage_cli.constants import CLOUD_LOCALHOST, CLOUD_TYPE_K8S
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import RenderStepOutput, TerminalOutputManager


def _add_helm_repositories() -> None:
    """Add required Helm repositories."""
    repos = [
        ("jetstack", REPO_JETSTACK_URL),
        ("prometheus-community", REPO_PROMETHEUS_URL),
        ("jamesbeedy-slinky-slurm", REPO_SLURM_URL),
    ]

    for name, url in repos:
        if not helm_repo_add(name, url, update=False):
            raise subprocess.CalledProcessError(
                1, ["helm", "repo", "add"], stderr=f"Failed to add repository {name}"
            )

    # Update all repositories at once
    if not helm_repo_update():
        raise subprocess.CalledProcessError(
            1, ["helm", "repo", "update"], stderr="Failed to update Helm repositories"
        )


def _install_cert_manager() -> None:
    """Install cert-manager with Helm."""
    set_values = {"crds.enabled": "true"}

    success = microk8s_deploy_chart(
        namespace=DEFAULT_NAMESPACE_CERT_MANAGER,
        release_name=DEFAULT_RELEASE_CERT_MANAGER,
        chart_repo=CHART_CERT_MANAGER,
        set_values=set_values,
        timeout="300s",
        upgrade=True,
    )

    if not success:
        raise subprocess.CalledProcessError(
            1, ["helm", "install"], stderr="Failed to install cert-manager"
        )


def _install_prometheus() -> None:
    """Install Prometheus with Helm."""
    success = microk8s_deploy_chart(
        namespace=DEFAULT_NAMESPACE_PROMETHEUS,
        release_name=DEFAULT_RELEASE_PROMETHEUS,
        chart_repo=CHART_PROMETHEUS,
        timeout="300s",
        upgrade=True,
    )

    if not success:
        raise subprocess.CalledProcessError(
            1, ["helm", "install"], stderr="Failed to install Prometheus"
        )


def _install_slurm_operator_crds() -> None:
    """Install SLURM operator CRDs."""
    # For CRDs, we need to use global namespace (pass empty string instead of None)
    success = microk8s_deploy_chart(
        namespace="",  # CRDs are cluster-scoped, empty string for global
        release_name=DEFAULT_RELEASE_SLURM_OPERATOR_CRDS,
        chart_repo=CHART_SLURM_OPERATOR_CRDS,
        timeout="300s",
        upgrade=True,
    )

    if not success:
        raise subprocess.CalledProcessError(
            1, ["helm", "install"], stderr="Failed to install SLURM operator CRDs"
        )


def _install_slurm_operator() -> None:
    """Install SLURM operator."""
    success = microk8s_deploy_chart(
        namespace=DEFAULT_NAMESPACE_SLINKY,
        release_name=DEFAULT_RELEASE_SLURM_OPERATOR,
        chart_repo=CHART_SLURM_OPERATOR,
        timeout="300s",
        upgrade=True,
    )

    if not success:
        raise subprocess.CalledProcessError(
            1, ["helm", "install"], stderr="Failed to install SLURM operator"
        )


def _install_slurm_cluster() -> None:
    """Install SLURM cluster."""
    success = microk8s_deploy_chart(
        namespace=DEFAULT_NAMESPACE_SLURM,
        release_name=DEFAULT_RELEASE_SLURM_CLUSTER,
        chart_repo=CHART_SLURM_CLUSTER,
        timeout="300s",
        upgrade=True,
    )

    if not success:
        raise subprocess.CalledProcessError(
            1, ["helm", "install"], stderr="Failed to install SLURM cluster"
        )


async def deploy(
    ctx: typer.Context,
    cluster_data: Dict[str, Any],
    verbose: bool = False,
    force: bool = False,
    renderer: Optional[RenderStepOutput] = None,
) -> None:
    """Deploy SLURM cluster on MicroK8s using Helm.

    This function is called by the Vantage cluster management system
    when creating a new cluster with this app.

    Args:
        ctx: Typer context containing settings and configuration
        cluster_data: Dictionary containing cluster configuration
        verbose: Whether to enable verbose output
        force: Whether to force deployment even if cluster exists
        renderer: Optional renderer for updating deployment progress

    Raises:
        typer.Exit: If deployment fails
    """
    console = ctx.obj.console if hasattr(ctx.obj, "console") else Console()
    json_mode = cluster_data.get("json_mode", False)

    # Validate cluster data and credentials
    cluster_data = validate_cluster_data(cluster_data, console)

    # Generate deployment ID and create deployment with init status
    cluster_name = cluster_data.get("name", "unknown")
    deployment_id = generate_default_deployment_name(APP_NAME, cluster_name)
    client_id = cluster_data.get("client_id", "unknown")

    create_deployment_with_init_status(
        deployment_id=deployment_id,
        app_name=APP_NAME,
        cluster_name=cluster_name,
        cluster_data=cluster_data,
        console=console,
        verbose=verbose,
        cloud=CLOUD_LOCALHOST,
        cloud_type=CLOUD_TYPE_K8S,
        k8s_namespaces=[],  # Will be populated as namespaces are created
    )

    if json_mode:
        # JSON mode: execute without UI panels
        try:
            # Check prerequisites
            checks = create_complete_prerequisite_checks()
            all_met, _ = check_prerequisites(checks, console, verbose=verbose, show_table=False)

            if not all_met:
                update_deployment_status(deployment_id, "failed", console)
                raise typer.Exit(1)

            # Perform deployment steps
            _add_helm_repositories()

            # Create namespaces
            for namespace in [
                DEFAULT_NAMESPACE_CERT_MANAGER,
                DEFAULT_NAMESPACE_PROMETHEUS,
                DEFAULT_NAMESPACE_SLINKY,
                DEFAULT_NAMESPACE_SLURM,
            ]:
                if not create_k8s_namespace(namespace):
                    update_deployment_status(deployment_id, "failed", console)
                    raise typer.Exit(1)

            # Install components
            _install_cert_manager()
            _install_prometheus()
            _install_slurm_operator_crds()
            _install_slurm_operator()
            _install_slurm_cluster()

            # Update deployment status to active on success
            update_deployment_status(deployment_id, "active", console)

        except Exception as e:
            update_deployment_status(deployment_id, "failed", console)
            error_msg = f"Deployment failed: {str(e)}"
            if renderer:
                renderer.json_bypass({"error": error_msg})
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)
    else:
        # Interactive mode with TerminalOutputManager
        with TerminalOutputManager(
            console=console,
            operation_name="🚀 SLURM MicroK8S Deployment Progress",
            verbose=verbose,
            json_output=getattr(ctx.obj, "json_output", False),
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
                            missing_tools.append(
                                f"{result.name}: {result.error_message or 'Missing'}"
                            )

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
                _add_helm_repositories()
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
                _install_cert_manager()
                output.success("cert-manager installed")
                time.sleep(1)

                # Step 5: Install Prometheus
                output.status("📊 Installing Prometheus...")
                _install_prometheus()
                output.success("Prometheus installed")
                time.sleep(1)

                # Step 6: Install SLURM operator CRDs
                output.status("⚙️ Installing SLURM operator CRDs...")
                _install_slurm_operator_crds()
                output.success("SLURM operator CRDs installed")
                time.sleep(1)

                # Step 7: Install SLURM operator
                output.status("🎛️ Installing SLURM operator...")
                _install_slurm_operator()
                output.success("SLURM operator installed")
                time.sleep(1)

                # Step 8: Install SLURM cluster
                output.status("🖥️ Installing SLURM cluster...")
                _install_slurm_cluster()
                output.success("SLURM cluster installed")
                time.sleep(1)

                # Step 9: Finalize
                output.status("🎉 Finalizing deployment...")
                update_deployment_status(deployment_id, "active", console)

                # Set beautiful success content
                output.set_final_content(
                    format_deployment_success_content(client_id), success=True
                )

            except Exception as e:
                update_deployment_status(deployment_id, "failed", console)
                error_msg = f"Deployment failed: {str(e)}"
                output.set_final_content(
                    format_deployment_failure_content(error_msg), success=False
                )
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

    cluster_data = generate_dev_cluster_data(cluster_name)
    if not dev_run:
        from vantage_cli.commands.cluster import utils as cluster_utils

        cluster_data = await cluster_utils.get_cluster_by_name(ctx=ctx, cluster_name=cluster_name)
        if cluster_data is None:
            raise ValueError(f"Cluster '{cluster_name}' not found")
    else:
        ctx.obj.console.print(
            f"[blue]Using dev run mode with dummy cluster data for '{cluster_name}'[/blue]"
        )

    await deploy(ctx=ctx, cluster_data=cluster_data)


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
