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
"""Utility functions for SLURM on MicroK8s localhost deployments."""

import json
import shutil
import subprocess
from pathlib import Path
from shutil import which
from textwrap import dedent
from typing import Any, Dict, List, Optional

import snick
import yaml
from rich.console import Console

from vantage_cli.clouds.utils import (
    PrerequisiteCheck,
    PrerequisiteStatus,
    check_prerequisites,
)
from vantage_cli.exceptions import Abort

from .constants import (
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


def check_microk8s_available() -> None:
    """Check if MicroK8s is available and provide installation instructions if not.

    Raises:
        Abort: If MicroK8s is not found, with installation instructions
    """
    if not shutil.which("microk8s"):
        message = snick.dedent(
            """
            • MicroK8s not found. Please install MicroK8s first.

            • To install MicroK8s, run the following command:
              sudo snap install microk8s --channel 1.29/stable --classic

            • Then enable required addons:
              sudo microk8s.enable hostpath-storage
              sudo microk8s.enable dns
              sudo microk8s.enable metallb:10.64.140.43-10.64.140.49

            """
        ).strip()

        raise Abort(
            message,
            subject="MicroK8s Required",
            log_message="MicroK8s binary not found",
        )


def check_microk8s_addons() -> None:
    """Check if required MicroK8s addons are enabled and provide installation help.

    Checks the following required addons:
    - dns: CoreDNS for cluster DNS resolution
    - hostpath-storage: Storage provisioner for persistent volumes
    - metallb: Load balancer for services
    - helm3: Helm package manager for application deployment

    Raises:
        Abort: If any required addons are missing, with installation instructions
    """
    required_addons = {
        "dns": {
            "description": "CoreDNS for cluster DNS resolution",
            "enable_command": "microk8s.enable dns",
        },
        "hostpath-storage": {
            "description": "Storage provisioner for persistent volumes",
            "enable_command": "sudo microk8s.enable hostpath-storage",
        },
        "metallb": {
            "description": "Load balancer for services",
            "enable_command": "microk8s.enable metallb:10.64.140.43-10.64.140.49",
            "note": "Adjust the IP range (10.64.140.43-10.64.140.49) to match your network",
        },
        "helm3": {
            "description": "Helm package manager for application deployment",
            "enable_command": "microk8s.enable helm3",
        },
    }

    try:
        # Get MicroK8s status in YAML format
        result = subprocess.run(
            ["microk8s", "status", "--format", "yaml"], capture_output=True, text=True, check=True
        )
        status_data = yaml.safe_load(result.stdout)
    except subprocess.CalledProcessError as e:
        raise Abort(
            "Failed to get MicroK8s status. Please ensure MicroK8s is properly installed and running.",
            subject="MicroK8s Status Error",
            log_message=f"microk8s status failed: {e}",
        )
    except yaml.YAMLError as e:
        raise Abort(
            "Failed to parse MicroK8s status output.",
            subject="MicroK8s Status Parse Error",
            log_message=f"YAML parse error: {e}",
        )

    # Check if MicroK8s is running
    if not status_data.get("microk8s", {}).get("running", False):
        raise Abort(
            "MicroK8s is not running. Please start it with: sudo microk8s start",
            subject="MicroK8s Not Running",
            log_message="MicroK8s service is not running",
        )

    # Get enabled addons
    enabled_addons: set[str] = set()
    addons_list = status_data.get("addons", [])
    for addon in addons_list:
        if addon.get("status") == "enabled":
            addon_name = addon.get("name")
            if addon_name:
                enabled_addons.add(addon_name)

    # Check for missing addons
    missing_addons: list[tuple[str, dict[str, str]]] = []
    enabled_status: list[str] = []

    for addon_name, addon_info in required_addons.items():
        if addon_name in enabled_addons:
            enabled_status.append(f"✓ {addon_name}: {addon_info['description']}")
        else:
            missing_addons.append((addon_name, addon_info))

    # Show status and handle missing addons
    if missing_addons:
        message_parts: list[str] = []

        if enabled_status:
            message_parts.append("✅ Enabled addons:")
            for status in enabled_status:
                message_parts.append(f"  {status}")
            message_parts.append("")

        message_parts.append("❌ Missing required addons:")
        for addon_name, addon_info in missing_addons:
            message_parts.append(f"  • {addon_name}: {addon_info['description']}")
            message_parts.append(f"    Command: {addon_info['enable_command']}")
            if "note" in addon_info:
                message_parts.append(f"    Note: {addon_info['note']}")

        message_parts.extend(
            ["", "Please enable all missing addons before proceeding with deployment."]
        )

        raise Abort(
            "\n".join(message_parts),
            subject="MicroK8s Addons Required",
            log_message=f"Missing addons: {[name for name, _ in missing_addons]}",
        )
    else:
        # All addons are enabled - could optionally show success message
        # For now, just return silently to continue with deployment
        pass


def check_existing_deployment() -> None:
    """Check if a SLURM deployment already exists on MicroK8s.

    Checks for the presence of 'slinky' and 'slurm' namespaces which indicate
    an existing SLURM deployment.

    Raises:
        Abort: If deployment already exists, with cleanup instructions
    """
    try:
        # Get list of namespaces
        result = subprocess.run(
            ["microk8s.kubectl", "get", "namespaces", "-o", "name"],
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse namespace names
        existing_namespaces: set[str] = set()
        for line in result.stdout.strip().split("\n"):
            if line.startswith("namespace/"):
                namespace_name = line.replace("namespace/", "")
                existing_namespaces.add(namespace_name)

        # Check for SLURM-related namespaces
        slurm_namespaces = {"slinky", "slurm"}
        found_namespaces = slurm_namespaces.intersection(existing_namespaces)

        if found_namespaces:
            namespace_list = "\n".join(
                f"                  • {ns}" for ns in sorted(found_namespaces)
            )
            message = dedent(
                f"""
                🔍 Existing SLURM deployment detected!

                Found the following SLURM-related namespaces:
                {namespace_list}

                📋  Options:

                1️⃣  Clean up existing deployment first:
                    vantage deployment slurm-microk8s-localhost cleanup

                2️⃣  Check current deployment status:
                    microk8s.kubectl get pods -n slinky
                    microk8s.kubectl get pods -n slurm

                3️⃣  Connect to existing deployment (if running):
                    # Get connection details
                    SLURM_LOGIN_IP="$(microk8s.kubectl get services -n slurm slurm-login-slinky -o jsonpath='{{.status.loadBalancer.ingress[0].ip}}')"
                    SLURM_LOGIN_PORT="$(microk8s.kubectl get services -n slurm slurm-login-slinky -o jsonpath='{{.spec.ports[0].port}}')"

                    # Connect via SSH
                    ssh -p ${{SLURM_LOGIN_PORT:-22}} ${{USER}}@${{SLURM_LOGIN_IP}}

                ℹ️  To proceed with a new deployment, please clean up the existing one first.
                """
            ).strip()

            raise Abort(
                message,
                subject="SLURM Deployment Already Exists",
                log_message=f"Found existing namespaces: {found_namespaces}",
            )

    except subprocess.CalledProcessError:
        # If kubectl command fails, it might mean MicroK8s is not running properly
        # Let the deployment continue and let other checks handle this
        pass
    except (OSError, FileNotFoundError):
        # kubectl command not found or other file system issues
        # Let the deployment continue and let other checks handle this
        pass


def is_ready(cluster_data: Dict[str, Any]) -> bool:
    """Check if the MicroK8s localhost cluster is ready and reachable.

    This function checks if:
    1. kubectl is available
    2. The namespace exists
    3. Key pods are running (slurm-operator, slurmctld, slurmd)

    Args:
        cluster_data: Dictionary containing cluster information including deployment_name

    Returns:
        True if cluster is ready and reachable, False otherwise
    """
    # Get the namespace from deployment_name
    namespace = cluster_data.get("deployment_name")
    if not namespace:
        # Try to derive from cluster name
        cluster_name = cluster_data.get("name")
        if cluster_name:
            namespace = f"slurm-{cluster_name}"
        else:
            return False

    # Check if kubectl is available
    kubectl = which("kubectl")
    if not kubectl:
        return False

    try:
        # Check if namespace exists
        result = subprocess.run(
            ["kubectl", "get", "namespace", namespace, "-o", "json"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return False

        # Check if key pods are running
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", namespace, "-o", "json"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return False

        pods_data = json.loads(result.stdout)
        pods = pods_data.get("items", [])

        if not pods:
            return False

        # Check for critical pods (slurm-operator, slurmctld, slurmd)
        required_pod_prefixes = ["slurm-operator", "slurmctld", "slurmd"]
        found_pods = dict.fromkeys(required_pod_prefixes, False)

        for pod in pods:
            pod_name = pod.get("metadata", {}).get("name", "")
            pod_status = pod.get("status", {}).get("phase", "")

            for prefix in required_pod_prefixes:
                if pod_name.startswith(prefix) and pod_status == "Running":
                    found_pods[prefix] = True

        # All required pods must be found and running
        return all(found_pods.values())

    except (
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
        json.JSONDecodeError,
        Exception,
    ):
        return False


def create_common_prerequisite_checks() -> List[PrerequisiteCheck]:
    """Create common prerequisite checks for MicroK8s deployments."""
    return [
        PrerequisiteCheck(
            name="microk8s",
            command=["microk8s", "status", "--wait-ready", "--timeout", "5"],
            version_command=["microk8s", "version"],
            installation_hint="Install MicroK8s: sudo snap install microk8s --classic",
            required=True,
        ),
        PrerequisiteCheck(
            name="docker",
            command=["docker", "--version"],
            version_command=["docker", "--version"],
            installation_hint="Install Docker: https://docs.docker.com/get-docker/",
            required=True,
        ),
        PrerequisiteCheck(
            name="microk8s helm",
            command=["microk8s", "helm", "version"],
            version_command=["microk8s", "helm", "version"],
            installation_hint="Enable helm addon: microk8s enable helm3",
            required=True,
        ),
        PrerequisiteCheck(
            name="kubectl",
            command=["microk8s", "kubectl", "version", "--client"],
            version_command=["microk8s", "kubectl", "version", "--client"],
            installation_hint="kubectl is available through microk8s",
            required=False,
        ),
    ]


def check_microk8s_addon_enabled(addon_name: str) -> bool:
    """Check if a specific MicroK8s addon is enabled.

    Args:
        addon_name: Name of the addon to check (e.g., 'dns', 'metallb', 'hostpath-storage')

    Returns:
        bool: True if addon is enabled, False otherwise
    """
    try:
        result = subprocess.run(
            ["microk8s", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return False

        # Parse the output to check if addon is enabled
        # MicroK8s status output shows enabled addons with their status
        lines = result.stdout.split("\n")
        for line in lines:
            if addon_name in line and ("enabled" in line.lower() or "running" in line.lower()):
                return True

        return False
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return False


def create_microk8s_addon_prerequisite_checks() -> List[PrerequisiteCheck]:
    """Create prerequisite checks for required MicroK8s addons."""
    return [
        PrerequisiteCheck(
            name="microk8s dns addon",
            command=[
                "sh",
                "-c",
                "microk8s status | awk '/enabled:/{flag=1; next} /disabled:/{flag=0} flag && /dns/' | grep -q dns && echo 'enabled' || exit 1",
            ],
            installation_hint="Enable DNS addon: microk8s enable dns",
            required=True,
        ),
        PrerequisiteCheck(
            name="microk8s metallb addon",
            command=[
                "sh",
                "-c",
                "microk8s status | awk '/enabled:/{flag=1; next} /disabled:/{flag=0} flag && /metallb/' | grep -q metallb && echo 'enabled' || exit 1",
            ],
            installation_hint="Enable MetalLB addon: microk8s enable metallb:10.64.140.43-10.64.140.49 (adjust IP range as needed)",
            required=True,
        ),
        PrerequisiteCheck(
            name="microk8s hostpath-storage addon",
            command=[
                "sh",
                "-c",
                "microk8s status | awk '/enabled:/{flag=1; next} /disabled:/{flag=0} flag && /hostpath-storage/' | grep -q hostpath-storage && echo 'enabled' || exit 1",
            ],
            installation_hint="Enable hostpath-storage addon: microk8s enable hostpath-storage",
            required=True,
        ),
    ]


def deploy_microk8s_stack(
    *,
    console: Console,
    verbose: bool,
    set_values: Dict[str, Any],
    chart_values: Dict[str, Any],
) -> None:
    """Execute the MicroK8s deployment workflow using CLI utilities only.

    Args:
        console: Rich console for output rendering
        verbose: Whether to display verbose output during checks
        set_values: Additional Helm values for the SLURM cluster chart
        chart_values: Base chart values for the SLURM cluster

    Raises:
        RuntimeError: If any deployment step fails
    """
    # Step 1: Verify prerequisites
    console.print("🔍 Checking prerequisites...", style="bold blue")
    checks = create_complete_prerequisite_checks()
    all_met, results = check_prerequisites(
        checks,
        console,
        verbose=verbose,
        show_table=False,
    )

    if not all_met:
        missing_tools = [
            f"{result.name}: {result.error_message or 'Missing'}"
            for result in results
            if result.status != PrerequisiteStatus.AVAILABLE
        ]
        raise RuntimeError("Missing prerequisites: " + "; ".join(missing_tools))

    console.print("[green]✓[/green] Prerequisites check passed")

    # Step 2: Configure Helm repositories
    console.print("📦 Setting up Helm repositories...", style="bold blue")
    repos = [
        ("jetstack", REPO_JETSTACK_URL),
        ("prometheus-community", REPO_PROMETHEUS_URL),
        ("jamesbeedy-slinky-slurm", REPO_SLURM_URL),
    ]
    try:
        add_helm_repositories(repos)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Helm repository configuration failed: {exc}") from exc

    console.print("[green]✓[/green] Helm repositories configured")

    # Step 3: Ensure required namespaces exist
    console.print("🔧 Creating Kubernetes namespaces...", style="bold blue")
    namespaces = [
        DEFAULT_NAMESPACE_CERT_MANAGER,
        DEFAULT_NAMESPACE_PROMETHEUS,
        DEFAULT_NAMESPACE_SLINKY,
        DEFAULT_NAMESPACE_SLURM,
    ]
    for namespace in namespaces:
        if not create_k8s_namespace(namespace):
            raise RuntimeError(f"Failed to create namespace '{namespace}'")
    console.print("[green]✓[/green] Namespaces ready")

    # Step 4: Install Prometheus stack
    console.print("📊 Installing Prometheus...", style="bold blue")
    install_prometheus(
        DEFAULT_NAMESPACE_PROMETHEUS,
        DEFAULT_RELEASE_PROMETHEUS,
        CHART_PROMETHEUS,
    )
    console.print("[green]✓[/green] Prometheus installed")

    # Step 5: Install SLURM operator components
    console.print("⚙️ Installing SLURM operator CRDs...", style="bold blue")
    install_slurm_operator_crds(
        DEFAULT_RELEASE_SLURM_OPERATOR_CRDS,
        CHART_SLURM_OPERATOR_CRDS,
    )
    console.print("[green]✓[/green] SLURM operator CRDs installed")

    console.print("🎛️ Installing SLURM operator...", style="bold blue")
    install_slurm_operator(
        DEFAULT_NAMESPACE_SLINKY,
        DEFAULT_RELEASE_SLURM_OPERATOR,
        CHART_SLURM_OPERATOR,
    )
    console.print("[green]✓[/green] SLURM operator installed")

    # Step 6: Install SLURM cluster
    console.print("🖥️ Installing SLURM cluster...", style="bold blue")
    install_slurm_cluster(
        DEFAULT_NAMESPACE_SLURM,
        DEFAULT_RELEASE_SLURM_CLUSTER,
        CHART_SLURM_CLUSTER,
        chart_values,
        set_values,
    )
    console.print("[green]✓[/green] SLURM cluster installed")


def create_complete_prerequisite_checks() -> List[PrerequisiteCheck]:
    """Create complete prerequisite checks including MicroK8s addons."""
    basic_checks = create_common_prerequisite_checks()
    addon_checks = create_microk8s_addon_prerequisite_checks()
    return basic_checks + addon_checks


def create_k8s_namespace(namespace: str) -> bool:
    """Create a Kubernetes namespace.

    Args:
        namespace: Name of the namespace to create

    Returns:
        bool: True if namespace was created or already exists, False if creation failed
    """
    try:
        subprocess.run(
            ["microk8s", "kubectl", "create", "namespace", namespace],
            capture_output=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        # Namespace might already exist, which is fine
        stderr_output = e.stderr.decode().strip() if e.stderr else ""
        if "already exists" in stderr_output:
            return True
        else:
            return False


def get_ssh_keys() -> Optional[str]:
    """Retrieve user's SSH public keys for SLURM cluster access."""
    user_ssh_rsa_pub_key = Path.home() / ".ssh" / "id_rsa.pub"
    user_ssh_ed25519_pub_key = Path.home() / ".ssh" / "id_ed25519.pub"

    ssh_authorized_keys: List[Any] = []

    if user_ssh_rsa_pub_key.exists():
        ssh_authorized_keys.append(user_ssh_rsa_pub_key.read_text().strip())
    if user_ssh_ed25519_pub_key.exists():
        ssh_authorized_keys.append(user_ssh_ed25519_pub_key.read_text().strip())

    if len(ssh_authorized_keys) > 0:
        return "\n".join(ssh_authorized_keys)

    return None


def helm_repo_add(repo_name: str, repo_url: str, update: bool = True) -> bool:
    """Add a Helm repository and optionally update.

    Args:
        repo_name: Name for the repository
        repo_url: URL of the repository
        update: Whether to run helm repo update after adding (default: True)

    Returns:
        bool: True if successful, False if failed
    """
    try:
        # Add the repository
        subprocess.run(
            ["microk8s", "helm", "repo", "add", repo_name, repo_url],
            capture_output=True,
            check=True,
        )

        # Update repositories if requested
        if update:
            subprocess.run(
                ["microk8s", "helm", "repo", "update"],
                capture_output=True,
                check=True,
            )

        return True
    except subprocess.CalledProcessError:
        return False


def helm_repo_update() -> bool:
    """Update all Helm repositories.

    Returns:
        bool: True if successful, False if failed
    """
    try:
        subprocess.run(
            ["microk8s", "helm", "repo", "update"],
            capture_output=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def microk8s_deploy_chart(
    namespace: str,
    release_name: str,
    chart_repo: str,
    chart_values: Optional[Dict[str, Any]] = None,
    set_values: Optional[Dict[str, str]] = None,
    timeout: str = "10m",
    upgrade: bool = True,
) -> bool:
    """Deploy a Helm chart using MicroK8s helm3.

    Args:
        namespace: Kubernetes namespace to deploy to (can be empty string for cluster-scoped resources like CRDs)
        release_name: Name for the Helm release
        chart_repo: Chart repository URL (e.g., "oci://registry-1.docker.io/bitnamicharts/keycloak")
        chart_values: Optional dictionary containing chart values (will be passed as YAML)
        set_values: Optional dictionary of key-value pairs for --set parameters
        timeout: Helm timeout duration (default: "10m")
        upgrade: Whether to use upgrade --install (default: True)

    Returns:
        bool: True if deployment succeeded, False otherwise
    """
    try:
        # Build the command
        cmd: List[str] = [
            "microk8s",
            "helm",
            "upgrade" if upgrade else "install",
            release_name,
            chart_repo,
            "--wait",
            f"--timeout={timeout}",
        ]

        # Add --install flag for upgrade mode
        if upgrade:
            cmd.insert(3, "--install")

        # Add namespace parameter only if namespace is specified (not empty for CRDs)
        if namespace:
            cmd.extend([f"--namespace={namespace}"])

        # Add --set parameters if provided
        if set_values:
            for key, value in set_values.items():
                cmd.extend(["--set", f"{key}={value}"])

        # Prepare input for values file
        input_data = None
        if chart_values:
            cmd.extend(["--values", "-"])
            input_data = yaml.dump(chart_values).encode("utf-8")

        subprocess.run(
            cmd,
            input=input_data,
            capture_output=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def add_helm_repositories(repos: List[tuple[str, str]]) -> None:
    """Add required Helm repositories.

    Args:
        repos: List of (name, url) tuples for Helm repositories to add

    Raises:
        subprocess.CalledProcessError: If adding or updating repositories fails
    """
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


def install_cert_manager(
    namespace: str,
    release_name: str,
    chart_repo: str,
) -> None:
    """Install cert-manager with Helm.

    Args:
        namespace: Kubernetes namespace to install into
        release_name: Name for the Helm release
        chart_repo: Chart repository URL

    Raises:
        subprocess.CalledProcessError: If installation fails
    """
    set_values = {"crds.enabled": "true"}

    success = microk8s_deploy_chart(
        namespace=namespace,
        release_name=release_name,
        chart_repo=chart_repo,
        set_values=set_values,
        timeout="300s",
        upgrade=True,
    )

    if not success:
        raise subprocess.CalledProcessError(
            1, ["helm", "install"], stderr="Failed to install cert-manager"
        )


def install_prometheus(
    namespace: str,
    release_name: str,
    chart_repo: str,
) -> None:
    """Install Prometheus with Helm.

    Args:
        namespace: Kubernetes namespace to install into
        release_name: Name for the Helm release
        chart_repo: Chart repository URL

    Raises:
        subprocess.CalledProcessError: If installation fails
    """
    success = microk8s_deploy_chart(
        namespace=namespace,
        release_name=release_name,
        chart_repo=chart_repo,
        timeout="300s",
        upgrade=True,
    )

    if not success:
        raise subprocess.CalledProcessError(
            1, ["helm", "install"], stderr="Failed to install Prometheus"
        )


def install_slurm_operator_crds(
    release_name: str,
    chart_repo: str,
) -> None:
    """Install SLURM operator CRDs.

    Args:
        release_name: Name for the Helm release
        chart_repo: Chart repository URL

    Raises:
        subprocess.CalledProcessError: If installation fails
    """
    # For CRDs, we need to use global namespace (pass empty string instead of None)
    success = microk8s_deploy_chart(
        namespace="",  # CRDs are cluster-scoped, empty string for global
        release_name=release_name,
        chart_repo=chart_repo,
        timeout="300s",
        upgrade=True,
    )

    if not success:
        raise subprocess.CalledProcessError(
            1, ["helm", "install"], stderr="Failed to install SLURM operator CRDs"
        )


def install_slurm_operator(
    namespace: str,
    release_name: str,
    chart_repo: str,
) -> None:
    """Install SLURM operator.

    Args:
        namespace: Kubernetes namespace to install into
        release_name: Name for the Helm release
        chart_repo: Chart repository URL

    Raises:
        subprocess.CalledProcessError: If installation fails
    """
    success = microk8s_deploy_chart(
        namespace=namespace,
        release_name=release_name,
        chart_repo=chart_repo,
        timeout="300s",
        upgrade=True,
    )

    if not success:
        raise subprocess.CalledProcessError(
            1, ["helm", "install"], stderr="Failed to install SLURM operator"
        )


def install_slurm_cluster(
    namespace: str,
    release_name: str,
    chart_repo: str,
    chart_values: Dict[str, Any],
    set_values: Optional[Dict[str, str]] = None,
) -> None:
    """Install SLURM cluster.

    Args:
        namespace: Kubernetes namespace to install into
        release_name: Name for the Helm release
        chart_repo: Chart repository URL
        chart_values: Dictionary of chart values
        set_values: Optional dictionary of additional values to set

    Raises:
        subprocess.CalledProcessError: If installation fails
    """
    success = microk8s_deploy_chart(
        namespace=namespace,
        release_name=release_name,
        chart_repo=chart_repo,
        chart_values=chart_values,
        set_values=set_values or {},
        timeout="300s",
        upgrade=True,
    )

    if not success:
        raise subprocess.CalledProcessError(
            1, ["helm", "install"], stderr="Failed to install SLURM cluster"
        )
