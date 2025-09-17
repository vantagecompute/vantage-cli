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
"""MicroK8s application support for deploying the Slurm Operator & Slurm cluster.

Implements the manual steps documented in the local README:

1. Add Helm repositories (jetstack, prometheus-community)
2. Install cert-manager, Prometheus stack, Slurm Operator CRDs
3. Install a Slurm cluster release

microk8s.helm repo add jetstack https://charts.jetstack.io
microk8s.helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
microk8s.helm repo add jamesbeedy-slinky-slurm https://jamesbeedy.github.io/slurm-operator

microk8s.helm repo update

# Cert Manager
microk8s.helm install cert-manager oci://quay.io/jetstack/charts/cert-manager \
    --set 'crds.enabled=true' \
    --namespace cert-manager \
    --create-namespace \
    --version v1.18.2

# Prometheus
microk8s.helm install prometheus prometheus-community/kube-prometheus-stack \
    --namespace prometheus \
    --create-namespace

# Install slurm crds
# Patch until the crds are available upstream
microk8s.helm install slurm-operator-crds jamesbeedy-slinky-slurm/slurm-operator-crds --version 0.4.0

# Install slurm-operator
curl -L https://raw.githubusercontent.com/jamesbeedy/slurm-operator/refs/tags/v0.4.0/helm/slurm-operator/values.yaml -o values-operator.yaml
microk8s.helm install slurm-operator oci://ghcr.io/slinkyproject/charts/slurm-operator --values=values-operator.yaml --version=0.4.0 --namespace=slinky --create-namespace

# Install SLURM Cluster
curl -L https://raw.githubusercontent.com/jamesbeedy/slurm-operator/refs/tags/v0.4.0/helm/slurm/values.yaml -o values-slurm.yaml
microk8s.helm install slurm oci://ghcr.io/slinkyproject/charts/slurm --values=values-slurm.yaml --version=0.4.0 --namespace=slurm --create-namespace

Notes:
- These steps are inherently idempotent; failures on already-installed/ enabled
  components are treated as warnings (not fatal) when safe.
- This command invokes system binaries (sudo microk8s.* & curl). The user must
  have the appropriate privileges. We intentionally keep the logic simple and
  transparent; advanced lifecycle management belongs in a dedicated orchestrator.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from typing_extensions import Annotated

from vantage_cli.apps.common import (
    generate_dev_cluster_data,
    validate_client_credentials,
    validate_cluster_data,
)
from vantage_cli.apps.slurm_microk8s_localhost.utils import (
    get_chart_values_slurm_cluster,
    get_chart_values_slurm_operator,
)
from vantage_cli.config import attach_settings

console = Console()


def _run(
    command: list[str],
    console: Console,
    allow_fail: bool = False,
    env: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """Run a subprocess command with error handling and return the result.

    Args:
        command: List of command arguments to execute
        console: Rich console for output
        allow_fail: If True, non-zero exit codes don't raise exceptions
        env: Optional environment variables

    Returns:
        subprocess.CompletedProcess: Result of the command execution

    Raises:
        typer.Exit: If command fails and allow_fail is False
    """
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, env=env)
        if result.returncode != 0:
            stderr_msg = getattr(result, "stderr", "Unknown error")
            if allow_fail:
                console.print(
                    f"[yellow]Warning: Command failed (non-fatal): {' '.join(command)}[/yellow]"
                )
                console.print(f"[yellow]Error: {stderr_msg}[/yellow]")
            else:
                console.print(f"[red]Error running command: {' '.join(command)}[/red]")
                console.print(f"[red]Error: {stderr_msg}[/red]")
                raise typer.Exit(code=result.returncode)
        else:
            console.print(f"[green]✓ {' '.join(command)}[/green]")
        return result
    except FileNotFoundError:
        console.print(f"[red]Error: Command not found: {command[0]}[/red]")
        if allow_fail:
            return subprocess.CompletedProcess(command, 127, stdout="", stderr="Command not found")
        raise typer.Exit(code=1)


def _run_command(command: list[str], allow_fail: bool = False) -> None:
    """Run a subprocess command with error handling.

    Args:
        command: List of command arguments to execute
        allow_fail: If True, non-zero exit codes are treated as warnings

    Raises:
        typer.Exit: If command fails and allow_fail is False
    """
    _run(command, console, allow_fail)


async def deploy(ctx: typer.Context, cluster_data: Dict[str, Any]) -> None:
    """Deploy SLURM cluster on MicroK8s using Helm.

    Implements the steps documented in the module docstring:
    1. Check for required binaries (microk8s, helm)
    2. Add Helm repositories
    3. Install cert-manager, Prometheus, and SLURM components
    4. Deploy SLURM cluster with generated values

    Args:
        ctx: Typer context containing settings and configuration
        cluster_data: Dictionary containing cluster configuration (optional for MicroK8s)

    Raises:
        typer.Exit: If deployment fails due to missing dependencies or command errors
    """
    console.print(Panel("MicroK8s SLURM Application"))
    console.print("Deploying SLURM cluster on MicroK8s...")

    # Check for required binaries
    if not shutil.which("microk8s"):
        console.print("[red]Error: microk8s not found. Please install MicroK8s first.[/red]")
        raise typer.Exit(code=1)

    # Verify microk8s.helm is available (we only use microk8s.helm, not standalone helm)
    console.print("✓ microk8s.helm version")
    _run_command(["microk8s.helm", "version"])

    # Validate cluster data if provided (optional for localhost deployment)
    cluster_data = validate_cluster_data(cluster_data, console)
    client_id, client_secret = validate_client_credentials(cluster_data, console)

    # Get client secret from API if not in cluster data (import locally to avoid circular import)
    if not client_secret:
        from vantage_cli.commands.cluster import utils as cluster_utils

        client_secret = await cluster_utils.get_cluster_client_secret(ctx=ctx, client_id=client_id)

    console.print(
        f"[blue]Deploying for cluster: {cluster_data.get('name', 'unknown')} (client: {client_id[:8]}...)[/blue]"
    )

    # Check MicroK8s status first (fatal if not ready)
    # console.print("Checking MicroK8s status...")
    _run_command(["microk8s", "status", "--wait-ready"])

    # Enable required MicroK8s addons (allow failures as they might already be enabled)
    # console.print("Enabling MicroK8s addons...")
    # _run_command(["microk8s", "enable", "dns"], allow_fail=True)
    # _run_command(["microk8s", "enable", "storage"], allow_fail=True)
    # _run_command(["microk8s", "enable", "helm3"], allow_fail=True)

    # Add Helm repositories
    console.print("Adding Helm repositories...")
    _run_command(
        ["microk8s.helm", "repo", "add", "jetstack", "https://charts.jetstack.io"], allow_fail=True
    )
    _run_command(
        [
            "microk8s.helm",
            "repo",
            "add",
            "prometheus-community",
            "https://prometheus-community.github.io/helm-charts",
        ],
        allow_fail=True,
    )
    _run_command(
        [
            "microk8s.helm",
            "repo",
            "add",
            "jamesbeedy-slinky-slurm",
            "https://jamesbeedy.github.io/slurm-operator",
        ],
        allow_fail=True,
    )

    # Update Helm repositories
    console.print("Updating Helm repositories...")
    _run_command(["microk8s.helm", "repo", "update"], allow_fail=True)

    # Install cert-manager
    console.print("Installing cert-manager...")
    _run_command(
        [
            "microk8s.helm",
            "install",
            "cert-manager",
            "oci://quay.io/jetstack/charts/cert-manager",
            "--set",
            "crds.enabled=true",
            "--namespace",
            "cert-manager",
            "--create-namespace",
            "--version",
            "v1.18.2",
        ],
        allow_fail=True,
    )

    # Install Prometheus
    console.print("Installing Prometheus...")
    _run_command(
        [
            "microk8s.helm",
            "install",
            "prometheus",
            "prometheus-community/kube-prometheus-stack",
            "--namespace",
            "prometheus",
            "--create-namespace",
        ],
        allow_fail=True,
    )

    # Install SLURM operator CRDs
    console.print("Installing SLURM operator CRDs...")
    _run_command(
        [
            "microk8s.helm",
            "install",
            "slurm-operator-crds",
            "jamesbeedy-slinky-slurm/slurm-operator-crds",
            "--version",
            "0.4.0",
        ],
        allow_fail=True,
    )

    slurm_operator_chart_values = get_chart_values_slurm_operator()
    slurm_operator_values_yaml = yaml.dump(slurm_operator_chart_values)
    tmp_file_operator_values = Path("/home/bdx/myslurmoperatorchartvalues.yaml")
    tmp_file_operator_values.write_text(slurm_operator_values_yaml)
    tmp_file_operator_values.chmod(0o600)
    # Install SLURM operator
    console.print("Installing SLURM operator...")
    _run_command(
        [
            "microk8s.helm",
            "install",
            "slurm-operator",
            "oci://ghcr.io/slinkyproject/charts/slurm-operator",
            f"--values={tmp_file_operator_values}",
            "--version=0.4.0",
            "--namespace=slinky",
            "--create-namespace",
        ],
        allow_fail=True,
    )
    # Patchable sleep for tests
    try:
        import sys
        from time import sleep

        if "pytest" in sys.modules:
            sleep(0.1)
        else:
            sleep(20)
    except ImportError:
        pass

    slurm_cluster_chart_values = get_chart_values_slurm_cluster()

    user_ssh_rsa_pub_key = Path.home() / ".ssh" / "id_rsa.pub"
    user_ssh_ed25519_pub_key = Path.home() / ".ssh" / "id_ed25519.pub"

    ssh_authorized_keys = []

    if user_ssh_rsa_pub_key.exists():
        ssh_authorized_keys.append(user_ssh_rsa_pub_key.read_text().strip())
        console.print(f"[blue]Found SSH RSA public key: {user_ssh_rsa_pub_key}[/blue]")
    if user_ssh_ed25519_pub_key.exists():
        ssh_authorized_keys.append(user_ssh_ed25519_pub_key.read_text().strip())
        console.print(f"[blue]Found SSH ED25519 public key: {user_ssh_ed25519_pub_key}[/blue]")

    if len(ssh_authorized_keys) > 0:
        console.print("[blue]Using SSH public keys:[/blue]")
        for key in ssh_authorized_keys:
            console.print(f" - {key}")
        slurm_cluster_chart_values["loginsets"]["slinky"]["rootSshAuthorizedKeys"] = "\n".join(
            ssh_authorized_keys
        )
    slurm_cluster_chart_values["loginsets"]["slinky"]["login"]["env"] = [
        {"name": "OIDC_CLIENT_ID", "value": client_id},
        {"name": "OIDC_CLIENT_SECRET", "value": client_secret},
        {"name": "OIDC_DOMAIN", "value": ctx.obj.settings.oidc_domain},
        {"name": "DEFAULT_SLURM_WORK_DIR", "value": "/tmp"},
        {"name": "TASK_JOBS_INTERVAL_SECONDS", "value": "10"},
    ]

    slurm_cluster_values_yaml = yaml.dump(slurm_cluster_chart_values)
    tmp_slurm_cluster_values = Path("/home/bdx/myslurmclusterchartvalues.yaml")
    tmp_slurm_cluster_values.write_text(slurm_cluster_values_yaml)
    tmp_slurm_cluster_values.chmod(0o600)
    # Install SLURM cluster
    console.print("Installing SLURM cluster...")
    _run_command(
        [
            "microk8s.helm",
            "install",
            "slurm",
            "oci://ghcr.io/slinkyproject/charts/slurm",
            f"--values={tmp_slurm_cluster_values}",
            "--version=0.4.0",
            "--namespace=slurm",
            "--create-namespace",
        ],
        allow_fail=True,
    )

    console.print("[green]✅ MicroK8s SLURM deployment completed successfully![/green]")
    console.print("[green]✅ MicroK8s SLURM operator namespace: slinky![/green]")
    console.print("[green]✅ MicroK8s SLURM cluster namespace: slurm![/green]")
    console.print("[green]✅ MicroK8s Prometheus namespace: prometheus![/green]")
    console.print("[green]✅ MicroK8s Cert Manager namespace: cert-manager![/green]")

    console.print(
        "[blue]Use 'microk8s.kubectl get pods -A --namespace slurm' to check pod status[/blue]"
    )


# Typer CLI commands
@attach_settings
async def deploy_command(
    ctx: typer.Context,
    cluster_name: Annotated[
        str,
        typer.Argument(help="Name of the cluster to deploy"),
    ],
    dev_run: Annotated[
        bool, typer.Option("--dev-run", help="Use dummy cluster data for local development")
    ] = False,
) -> None:
    """Deploy a Vantage SLURM cluster on MicroK8s."""
    console.print(Panel("MicroK8s SLURM Application"))
    console.print("Deploying MicroK8s SLURM application...")

    cluster_data = generate_dev_cluster_data(cluster_name)
    if not dev_run:
        from vantage_cli.commands.cluster import utils as cluster_utils

        cluster_data = await cluster_utils.get_cluster_by_name(ctx=ctx, cluster_name=cluster_name)
        if cluster_data is None:
            raise ValueError(f"Cluster '{cluster_name}' not found")
    else:
        console.print(
            f"[blue]Using dev run mode with dummy cluster data for '{cluster_name}'[/blue]"
        )

    await deploy(ctx=ctx, cluster_data=cluster_data)


async def cleanup_microk8s_localhost(cluster_data: Dict[str, Any]) -> None:
    """Clean up a MicroK8s localhost deployment by deleting the namespaces.

    This function deletes the namespaces created during deployment:
    - cert-manager
    - prometheus
    - slinky
    - slurm

    Args:
        cluster_data: Dictionary containing deployment metadata with deployment_name

    Raises:
        Exception: If cleanup fails
    """
    console = Console()

    # Get deployment name from cluster data
    deployment_name = cluster_data.get("deployment_name", "")
    if not deployment_name:
        console.print("[red]Error: No deployment_name found in cluster data[/red]")
        raise Exception("Missing deployment_name in cluster data")

    # Define the namespaces that were created during deployment
    namespaces = ["slurm", "slinky"]

    console.print(f"[yellow]Cleaning up MicroK8s deployment: {deployment_name}[/yellow]")

    # Check if microk8s is available
    if not shutil.which("microk8s"):
        console.print("[red]Error: microk8s not found. Cannot perform cleanup.[/red]")
        raise Exception("microk8s command not found")

    # Delete each namespace
    for namespace in namespaces:
        try:
            console.print(f"[yellow]Deleting namespace: {namespace}[/yellow]")
            result = _run(
                [
                    "microk8s",
                    "kubectl",
                    "delete",
                    "namespace",
                    namespace,
                    "--ignore-not-found=true",
                ],
                console,
                allow_fail=True,
            )

            if result.returncode == 0:
                console.print(f"[green]✓ Successfully deleted namespace '{namespace}'[/green]")
            else:
                console.print(
                    f"[yellow]Warning: Failed to delete namespace '{namespace}' (may not exist)[/yellow]"
                )

        except Exception as e:
            console.print(f"[yellow]Warning: Error deleting namespace '{namespace}': {e}[/yellow]")
            # Continue with other namespaces even if one fails

    console.print(
        f"[green]✓ MicroK8s cleanup completed for deployment '{deployment_name}'[/green]"
    )


# Typer CLI commands
@attach_settings
async def cleanup_command(
    ctx: typer.Context,
    deployment_name: Annotated[
        str,
        typer.Argument(help="Name of the deployment to clean up"),
    ],
    dev_run: Annotated[
        bool,
        typer.Option("--dev-run", help="Use dummy cluster data for development"),
    ] = False,
) -> None:
    """Clean up a Vantage SLURM cluster on MicroK8s."""
    from vantage_cli.commands.cluster import utils as cluster_utils

    console.print(Panel("MicroK8s SLURM Deployment Cleanup"))
    console.print(f"Cleanup MicroK8s SLURM Deployment {deployment_name}...")

    cluster_data = None

    if dev_run:
        console.print(
            f"[blue]Using dev run mode with dummy cluster data for '{deployment_name}'[/blue]"
        )
        cluster_data = generate_dev_cluster_data(deployment_name)
    else:
        cluster_data = await cluster_utils.get_cluster_by_name(
            ctx=ctx, cluster_name=deployment_name
        )

    if cluster_data is None:
        console.print(f"[red]Error: Cluster '{deployment_name}' not found[/red]")
        raise typer.Exit(1)

    await cleanup_microk8s_localhost(cluster_data=cluster_data)
