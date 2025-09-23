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
"""JupyterHub app for MicroK8s localhost deployment."""

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
from vantage_cli.apps.jupyterhub_microk8s_localhost.constants import (
    DEFAULT_KEYCLOAK_CLIENT_ID,
    DEFAULT_KEYCLOAK_URL,
    DEFAULT_NAMESPACE,
    DEFAULT_RELEASE_NAME,
    DEFAULT_SLURM_IMAGE,
)
from vantage_cli.apps.jupyterhub_microk8s_localhost.render import (
    format_deployment_failure_content,
    format_deployment_success_content,
)
from vantage_cli.apps.utils import (
    PrerequisiteStatus,
    check_prerequisites,
    create_complete_prerequisite_checks,
    create_k8s_namespace,
    helm_repo_add,
    microk8s_deploy_chart,
)
from vantage_cli.config import attach_settings
from vantage_cli.constants import CLOUD_LOCALHOST, CLOUD_TYPE_K8S
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import RenderStepOutput, TerminalOutputManager

APP_NAME = "jupyterhub-microk8s-localhost"


def _add_jupyterhub_repository() -> None:
    """Add JupyterHub Helm repository."""
    if not helm_repo_add("jupyterhub", "https://hub.jupyter.org/helm-chart/"):
        raise subprocess.CalledProcessError(
            1, ["helm", "repo", "add"], stderr="Failed to add JupyterHub repository"
        )


def _deploy_jupyterhub_chart(namespace: str, release_name: str) -> None:
    """Deploy JupyterHub using Helm chart."""
    set_values = {
        "hub.config.Authenticator.admin_users[0]": "admin",
        "hub.config.DummyAuthenticator.password": "admin",
        "hub.config.JupyterHub.authenticator_class": "dummy",
    }

    success = microk8s_deploy_chart(
        namespace=namespace,
        release_name=release_name,
        chart_repo="jupyterhub/jupyterhub",
        set_values=set_values,
        timeout="300s",
    )

    if not success:
        raise subprocess.CalledProcessError(
            1, ["helm", "upgrade"], stderr="Failed to deploy JupyterHub chart"
        )


async def deploy(
    ctx: typer.Context,
    cluster_data: Dict[str, Any],
    verbose: bool = False,
    force: bool = False,
    renderer: Optional[RenderStepOutput] = None,
) -> None:
    """Deploy JupyterHub on MicroK8s for cluster management.

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

    namespace = cluster_data.get("namespace", DEFAULT_NAMESPACE)
    release_name = cluster_data.get("release_name", DEFAULT_RELEASE_NAME)

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
            _add_jupyterhub_repository()

            if not create_k8s_namespace(namespace):
                update_deployment_status(deployment_id, "failed", console)
                raise typer.Exit(1)

            _deploy_jupyterhub_chart(namespace, release_name)

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
            operation_name="🚀 JupyterHub MicroK8S Deployment Progress",
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

                # Step 2: Add JupyterHub repository
                output.status("📦 Adding JupyterHub Helm repository...")
                _add_jupyterhub_repository()
                output.success("JupyterHub repository added")
                time.sleep(1)

                # Step 3: Create namespace
                output.status(f"🔧 Creating namespace '{namespace}'...")
                if not create_k8s_namespace(namespace):
                    error_msg = f"Failed to create namespace '{namespace}'"
                    output.set_final_content(
                        format_deployment_failure_content(error_msg), success=False
                    )
                    update_deployment_status(deployment_id, "failed", console)
                    raise typer.Exit(1)
                output.success(f"Namespace '{namespace}' created")
                time.sleep(1)

                # Step 4: Deploy JupyterHub
                output.status("🚀 Deploying JupyterHub with Helm...")
                _deploy_jupyterhub_chart(namespace, release_name)
                output.success("JupyterHub deployed successfully")
                time.sleep(1)

                # Step 5: Finalize
                output.status("🎉 Finalizing deployment...")
                update_deployment_status(deployment_id, "active", console)

                # Set beautiful success content
                output.set_final_content(
                    format_deployment_success_content(namespace, release_name), success=True
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
    namespace: Annotated[
        str, typer.Option("--namespace", "-n", help="Kubernetes namespace")
    ] = DEFAULT_NAMESPACE,
    release_name: Annotated[
        str, typer.Option("--release-name", "-r", help="Helm release name")
    ] = DEFAULT_RELEASE_NAME,
    keycloak_url: Annotated[
        str, typer.Option("--keycloak-url", help="Keycloak server URL")
    ] = DEFAULT_KEYCLOAK_URL,
    keycloak_client_id: Annotated[
        str, typer.Option("--keycloak-client-id", help="Keycloak client ID")
    ] = DEFAULT_KEYCLOAK_CLIENT_ID,
    keycloak_client_secret: Annotated[
        Optional[str], typer.Option("--keycloak-client-secret", help="Keycloak client secret")
    ] = None,
    slurm_image: Annotated[
        str, typer.Option("--slurm-image", help="Slurm sidecar container image")
    ] = DEFAULT_SLURM_IMAGE,
    sssd_config: Annotated[
        Optional[str],
        typer.Option("--sssd-config", help="SSSD configuration content (multiline string)"),
    ] = None,
) -> None:
    """Deploy JupyterHub to MicroK8s."""
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

    # Add deployment-specific config to cluster data
    cluster_data.update(
        {
            "namespace": namespace,
            "release_name": release_name,
            "keycloak_url": keycloak_url,
            "keycloak_client_id": keycloak_client_id,
            "keycloak_client_secret": keycloak_client_secret,
            "slurm_image": slurm_image,
            "sssd_conf": sssd_config,
        }
    )

    await deploy(ctx=ctx, cluster_data=cluster_data)


@handle_abort
@attach_settings
async def status_command(
    ctx: typer.Context,
    namespace: Annotated[str, typer.Option(help="Kubernetes namespace")] = DEFAULT_NAMESPACE,
) -> None:
    """Check JupyterHub deployment status."""
    console = ctx.obj.console if hasattr(ctx.obj, "console") else Console()

    try:
        result = subprocess.run(
            ["microk8s", "kubectl", "get", "deployment", "-n", namespace],
            capture_output=True,
            text=True,
            check=True,
        )
        console.print(f"[green]✓[/green] JupyterHub deployment status in namespace '{namespace}':")
        console.print(result.stdout)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗[/red] Failed to get deployment status: {e}")
        raise typer.Exit(1)


@handle_abort
@attach_settings
async def remove_command(
    ctx: typer.Context,
    namespace: Annotated[str, typer.Option(help="Kubernetes namespace")] = DEFAULT_NAMESPACE,
    release_name: Annotated[str, typer.Option(help="Helm release name")] = DEFAULT_RELEASE_NAME,
    force: Annotated[bool, typer.Option(help="Force removal without confirmation")] = False,
) -> None:
    """Remove JupyterHub deployment."""
    console = ctx.obj.console if hasattr(ctx.obj, "console") else Console()

    if not force:
        confirm = typer.confirm(
            f"Are you sure you want to remove JupyterHub deployment '{release_name}' from namespace '{namespace}'?"
        )
        if not confirm:
            console.print("Operation cancelled.")
            return

    try:
        subprocess.run(
            ["microk8s", "helm", "uninstall", release_name, "-n", namespace],
            capture_output=True,
            check=True,
        )
        console.print(
            f"[green]✓[/green] Successfully removed JupyterHub deployment '{release_name}' from namespace '{namespace}'"
        )
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗[/red] Failed to remove deployment: {e}")
        raise typer.Exit(1)
