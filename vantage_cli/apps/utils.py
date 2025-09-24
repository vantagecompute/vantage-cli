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
"""Utility functions for MicroK8s deployment."""

import importlib
import importlib.util
import logging
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

from vantage_cli.constants import VANTAGE_CLI_DEV_APPS_DIR


class PrerequisiteStatus(Enum):
    """Status of a prerequisite check."""

    AVAILABLE = "available"
    MISSING = "missing"
    ERROR = "error"


@dataclass
class PrerequisiteResult:
    """Result of a prerequisite check."""

    name: str
    status: PrerequisiteStatus
    version: Optional[str] = None
    error_message: Optional[str] = None
    installation_hint: Optional[str] = None


@dataclass
class PrerequisiteCheck:
    """Definition of a prerequisite check."""

    name: str
    command: List[str]
    version_command: Optional[List[str]] = None
    installation_hint: Optional[str] = None
    required: bool = True


def check_prerequisites(
    checks: List[PrerequisiteCheck],
    console: Console,
    verbose: bool = False,
    show_table: bool = True,
) -> Tuple[bool, List[PrerequisiteResult]]:
    """Check multiple prerequisites and report results to the user.

    Args:
        checks: List of prerequisite checks to perform
        console: Console for output
        verbose: Whether to show verbose output
        show_table: Whether to display a results table

    Returns:
        Tuple of (all_requirements_met, list_of_results)
    """
    results = []
    all_required_met = True

    if verbose:
        console.print("[blue]ℹ[/blue] Checking prerequisites...")

    for check in checks:
        result = _check_single_prerequisite(check, verbose, console)
        results.append(result)

        if check.required and result.status != PrerequisiteStatus.AVAILABLE:
            all_required_met = False

    if show_table:
        _display_prerequisite_table(results, console)

    # Show installation hints for missing required tools
    missing_required = [
        r
        for r in results
        if r.status != PrerequisiteStatus.AVAILABLE
        and any(c.required for c in checks if c.name == r.name)
    ]

    if missing_required:
        console.print()
        console.print("[red]⚠ Missing required prerequisites:[/red]")
        for result in missing_required:
            console.print(f"  • {result.name}")
            if result.installation_hint:
                console.print(f"    💡 {result.installation_hint}")
        console.print()

    # Show summary
    if all_required_met:
        if verbose:
            console.print("[green]✓[/green] All required prerequisites are available!")
    else:
        console.print(
            "[red]✗[/red] Some required prerequisites are missing. Please install them before proceeding."
        )

    return all_required_met, results


def _clean_error_message(error_message: str) -> str:
    """Clean up error messages to show concise, readable output."""
    if not error_message:
        return "Command failed"

    # Handle common patterns
    if "not found" in error_message.lower():
        return "Command not found"

    # Handle multiline tracebacks - extract the most relevant line
    lines = error_message.strip().split("\n")
    if len(lines) > 3:  # If it's a long traceback
        # Look for common error patterns
        for line in lines:
            if "LookupError:" in line or "Error:" in line or "Exception:" in line:
                return line.strip()
        # If no specific error found, return a generic message
        return "Command failed with error"

    # For shorter messages, clean up but keep essential info
    cleaned = error_message.strip()
    if len(cleaned) > 100:  # Truncate very long messages
        cleaned = cleaned[:97] + "..."

    return cleaned


def _check_single_prerequisite(
    check: PrerequisiteCheck, verbose: bool, console: Console
) -> PrerequisiteResult:
    """Check a single prerequisite."""
    try:
        # Check if tool is available
        result = subprocess.run(check.command, capture_output=True, text=True, timeout=10)

        if result.returncode != 0:
            cleaned_error = _clean_error_message(result.stderr)
            if verbose:
                console.print(f"[yellow]⚠[/yellow] {check.name}: Command failed - {cleaned_error}")
            return PrerequisiteResult(
                name=check.name,
                status=PrerequisiteStatus.MISSING,
                error_message=cleaned_error,
                installation_hint=check.installation_hint,
            )

        # Get version if version command is provided
        version = None
        if check.version_command:
            try:
                version_result = subprocess.run(
                    check.version_command, capture_output=True, text=True, timeout=5
                )
                if version_result.returncode == 0:
                    version = version_result.stdout.strip().split("\n")[0]  # Take first line
            except Exception:
                pass  # Version check is optional

        if verbose:
            version_str = f" (version: {version})" if version else ""
            console.print(f"[green]✓[/green] {check.name}: Available{version_str}")

        return PrerequisiteResult(
            name=check.name,
            status=PrerequisiteStatus.AVAILABLE,
            version=version,
            installation_hint=check.installation_hint,
        )

    except subprocess.TimeoutExpired:
        if verbose:
            console.print(f"[red]✗[/red] {check.name}: Check timed out")
        return PrerequisiteResult(
            name=check.name,
            status=PrerequisiteStatus.ERROR,
            error_message="Check timed out",
            installation_hint=check.installation_hint,
        )
    except FileNotFoundError:
        if verbose:
            console.print(f"[red]✗[/red] {check.name}: Not found")
        return PrerequisiteResult(
            name=check.name,
            status=PrerequisiteStatus.MISSING,
            error_message="Command not found",
            installation_hint=check.installation_hint,
        )
    except Exception as e:
        cleaned_error = _clean_error_message(str(e))
        if verbose:
            console.print(f"[red]✗[/red] {check.name}: Error - {cleaned_error}")
        return PrerequisiteResult(
            name=check.name,
            status=PrerequisiteStatus.ERROR,
            error_message=cleaned_error,
            installation_hint=check.installation_hint,
        )


def _display_prerequisite_table(results: List[PrerequisiteResult], console: Console) -> None:
    """Display prerequisite check results in a table."""
    table = Table(title="Prerequisite Check Results")
    table.add_column("Tool", style="cyan", no_wrap=True)
    table.add_column("Status", style="bold")
    table.add_column("Version", style="dim")
    table.add_column("Notes", style="dim")

    for result in results:
        if result.status == PrerequisiteStatus.AVAILABLE:
            status = "[green]✓ Available[/green]"
        elif result.status == PrerequisiteStatus.MISSING:
            status = "[red]✗ Missing[/red]"
        else:
            status = "[yellow]⚠ Error[/yellow]"

        version = result.version or "-"
        notes = result.error_message or "-"

        table.add_row(result.name, status, version, notes)

    console.print()
    console.print(table)
    console.print()


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
            name="microk8s cert-manager addon",
            command=[
                "sh",
                "-c",
                "microk8s status | awk '/enabled:/{flag=1; next} /disabled:/{flag=0} flag && /cert-manager/' | grep -q cert-manager && echo 'enabled' || exit 1",
            ],
            installation_hint="Enable cert-manager addon: microk8s enable cert-manager",
            required=True,
        ),
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


def create_complete_prerequisite_checks() -> List[PrerequisiteCheck]:
    """Create complete prerequisite checks including MicroK8s addons."""
    basic_checks = create_common_prerequisite_checks()
    addon_checks = create_microk8s_addon_prerequisite_checks()
    return basic_checks + addon_checks


def create_custom_prerequisite_checks(
    include_basic: bool = True,
    include_addons: bool = True,
    additional_checks: Optional[List[PrerequisiteCheck]] = None,
) -> List[PrerequisiteCheck]:
    """Create customized prerequisite checks.

    Args:
        include_basic: Whether to include basic MicroK8s and Docker checks
        include_addons: Whether to include MicroK8s addon checks
        additional_checks: Additional custom prerequisite checks to include

    Returns:
        List of prerequisite checks
    """
    checks = []

    if include_basic:
        checks.extend(create_common_prerequisite_checks())

    if include_addons:
        checks.extend(create_microk8s_addon_prerequisite_checks())

    if additional_checks:
        checks.extend(additional_checks)

    return checks


def check_microk8s_available() -> bool:
    """Check if MicroK8s is available and running."""
    try:
        result = subprocess.run(
            ["microk8s", "status", "--wait-ready", "--timeout", "5"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_helm_available() -> bool:
    """Check if MicroK8s Helm is available."""
    try:
        result = subprocess.run(["microk8s", "helm", "version"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def get_namespace_status(namespace: str) -> bool:
    """Check if a namespace exists."""
    try:
        result = subprocess.run(
            ["microk8s", "kubectl", "get", "namespace", namespace], capture_output=True, text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def create_temp_config_file(content: str, suffix: str = ".yaml") -> Path:
    """Create a temporary configuration file with the given content."""
    temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False)
    temp_file.write(content)
    temp_file.flush()
    temp_file.close()
    return Path(temp_file.name)


def copy_secret_between_namespaces(secret_name: str, source_ns: str, target_ns: str) -> bool:
    """Copy a Kubernetes secret from one namespace to another."""
    try:
        # Export secret from source namespace
        result = subprocess.run(
            ["microk8s", "kubectl", "get", "secret", secret_name, "-n", source_ns, "-o", "yaml"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return False

        # Modify namespace and apply to target
        secret_yaml = result.stdout.replace(f"namespace: {source_ns}", f"namespace: {target_ns}")

        process = subprocess.run(
            ["microk8s", "kubectl", "apply", "-f", "-"],
            input=secret_yaml,
            text=True,
            capture_output=True,
        )

        return process.returncode == 0
    except Exception:
        return False


def get_loadbalancer_ip(service_name: str, namespace: str) -> Optional[str]:
    """Get the LoadBalancer IP for a service."""
    try:
        result = subprocess.run(
            [
                "microk8s",
                "kubectl",
                "get",
                "svc",
                service_name,
                "-n",
                namespace,
                "-o",
                "jsonpath={.status.loadBalancer.ingress[0].ip}",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return None
    except Exception:
        return None


def wait_for_pods_ready(namespace: str, label_selector: str, timeout: int = 300) -> bool:
    """Wait for pods with the given label selector to be ready."""
    try:
        result = subprocess.run(
            [
                "microk8s",
                "kubectl",
                "wait",
                "--for=condition=ready",
                "pod",
                "-l",
                label_selector,
                "-n",
                namespace,
                f"--timeout={timeout}s",
            ],
            capture_output=True,
            text=True,
        )

        return result.returncode == 0
    except Exception:
        return False


async def get_cluster_data(
    ctx: typer.Context, cluster_name: str, dev_run: bool, verbose: bool
) -> Dict[str, Any]:
    """Get cluster data either from dev mode or actual cluster lookup.

    Args:
        ctx: Typer context
        cluster_name: Name of the cluster
        dev_run: Whether to use dev mode
        verbose: Whether to show verbose output

    Returns:
        Dictionary containing cluster data

    Raises:
        ValueError: If cluster is not found in non-dev mode
    """
    from vantage_cli.apps.common import generate_dev_cluster_data

    cluster_data = generate_dev_cluster_data(cluster_name)
    if not dev_run:
        from vantage_cli.commands.cluster import utils as cluster_utils

        cluster_data = await cluster_utils.get_cluster_by_name(ctx=ctx, cluster_name=cluster_name)
        if cluster_data is None:
            raise ValueError(f"Cluster '{cluster_name}' not found")
    else:
        if verbose:
            ctx.obj.console.print(
                f"[blue]Using dev run mode with dummy cluster data for '{cluster_name}'[/blue]"
            )
    return cluster_data


def cleanup_helm_release(
    release_name: str, namespace: str, console: Console, verbose: bool
) -> None:
    """Remove existing Helm release.

    Args:
        release_name: Name of the Helm release
        namespace: Kubernetes namespace
        console: Console for output
        verbose: Whether to show verbose output
    """
    result = subprocess.run(
        ["microk8s", "helm3", "uninstall", release_name, "-n", namespace],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        if verbose:
            console.print(f"✅ Removed existing Helm release '{release_name}'")
    else:
        if verbose:
            console.print(f"ℹ No existing Helm release '{release_name}' found")


def cleanup_helm_secrets(
    release_name: str, namespace: str, console: Console, verbose: bool
) -> None:
    """Remove stuck Helm secrets.

    Args:
        release_name: Name of the Helm release
        namespace: Kubernetes namespace
        console: Console for output
        verbose: Whether to show verbose output
    """
    result = subprocess.run(
        ["microk8s", "kubectl", "get", "secrets", "-n", namespace, "-o", "name"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        helm_secrets = [
            line
            for line in result.stdout.split("\n")
            if "helm.release" in line and release_name in line
        ]
        for secret in helm_secrets:
            if secret.strip():
                secret_name = secret.replace("secret/", "")
                subprocess.run(
                    [
                        "microk8s",
                        "kubectl",
                        "delete",
                        "secret",
                        secret_name,
                        "-n",
                        namespace,
                    ],
                    capture_output=True,
                )
                if verbose:
                    console.print(f"✅ Removed stuck Helm secret '{secret_name}'")


def cleanup_configmaps(namespace: str, console: Console, verbose: bool) -> None:
    """Remove existing ConfigMaps.

    Args:
        namespace: Kubernetes namespace
        console: Console for output
        verbose: Whether to show verbose output
    """
    configmaps_to_remove = ["keycloak-realms"]
    for cm in configmaps_to_remove:
        result = subprocess.run(
            [
                "microk8s",
                "kubectl",
                "delete",
                "configmap",
                cm,
                "-n",
                namespace,
                "--ignore-not-found",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            if verbose:
                console.print(f"✅ Removed ConfigMap '{cm}'")


def perform_force_cleanup(
    release_name: str, namespace: str, console: Console, verbose: bool
) -> None:
    """Perform force cleanup of existing Keycloak resources.

    Args:
        release_name: Name of the Helm release
        namespace: Kubernetes namespace
        console: Console for output
        verbose: Whether to show verbose output
    """
    if verbose:
        console.print("🧹 Force cleanup enabled - removing existing Keycloak resources...")

    try:
        cleanup_helm_release(release_name, namespace, console, verbose)
        cleanup_helm_secrets(release_name, namespace, console, verbose)
        cleanup_configmaps(namespace, console, verbose)

        if verbose:
            console.print("✅ Force cleanup completed")
    except Exception as e:
        if verbose:
            console.print(f"⚠️ Warning during cleanup: {str(e)}")


def check_removal_confirmation(
    force: bool, release_name: str, namespace: str, console: Console
) -> None:
    """Check for removal confirmation unless force is specified."""
    if not force:
        response = typer.confirm(
            f"Are you sure you want to remove Keycloak deployment '{release_name}' from namespace '{namespace}'?"
        )
        if not response:
            console.print("🚫 Removal cancelled.")
            raise typer.Exit(0)


def check_namespace_exists(namespace: str, verbose: bool, console: Console) -> None:
    """Check if the namespace exists."""
    try:
        result = subprocess.run(
            ["microk8s", "kubectl", "get", "namespace", namespace],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Namespace '{namespace}' does not exist")
    except subprocess.CalledProcessError:
        raise RuntimeError(f"Failed to check namespace '{namespace}'")


def remove_helm_release(
    release_name: str, namespace: str, verbose: bool, console: Console
) -> None:
    """Remove the Helm release."""
    try:
        result = subprocess.run(
            ["microk8s", "helm", "uninstall", release_name, "-n", namespace],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            if verbose:
                console.print(f"✅ Helm release '{release_name}' removed")
        elif "not found" in result.stderr:
            if verbose:
                console.print(f"ℹ️ Helm release '{release_name}' was not found (already removed)")
        else:
            if verbose:
                console.print(f"⚠️ Helm removal warning: {result.stderr}")
    except Exception as e:
        raise RuntimeError(f"Failed to remove Helm release: {str(e)}")


def cleanup_resources(namespace: str, verbose: bool, console: Console) -> None:
    """Clean up remaining Kubernetes resources."""
    cleanup_commands = [
        (
            [
                "microk8s",
                "kubectl",
                "delete",
                "pods",
                "--all",
                "-n",
                namespace,
                "--ignore-not-found",
            ],
            "pods",
        ),
        (
            [
                "microk8s",
                "kubectl",
                "delete",
                "services",
                "--all",
                "-n",
                namespace,
                "--ignore-not-found",
            ],
            "services",
        ),
        (
            [
                "microk8s",
                "kubectl",
                "delete",
                "configmaps",
                "--all",
                "-n",
                namespace,
                "--ignore-not-found",
            ],
            "configmaps",
        ),
        (
            [
                "microk8s",
                "kubectl",
                "delete",
                "secrets",
                "--all",
                "-n",
                namespace,
                "--ignore-not-found",
            ],
            "secrets",
        ),
        (
            [
                "microk8s",
                "kubectl",
                "delete",
                "persistentvolumeclaims",
                "--all",
                "-n",
                namespace,
                "--ignore-not-found",
            ],
            "PVCs",
        ),
    ]

    for cmd, resource_type in cleanup_commands:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if verbose:
                if result.returncode == 0:
                    console.print(f"✅ Cleaned up {resource_type}")
                else:
                    console.print(f"ℹ️ No {resource_type} to clean up")
        except subprocess.TimeoutExpired:
            if verbose:
                console.print(f"⚠️ Cleanup timeout for {resource_type}")
        except Exception:
            pass  # Ignore cleanup errors


def remove_namespace(namespace: str, verbose: bool, console: Console) -> None:
    """Remove the Kubernetes namespace."""
    try:
        result = subprocess.run(
            [
                "microk8s",
                "kubectl",
                "delete",
                "namespace",
                namespace,
                "--ignore-not-found",
                "--timeout=60s",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            if verbose:
                console.print(f"✅ Namespace '{namespace}' removed")
        elif "not found" in result.stderr:
            if verbose:
                console.print(f"ℹ️ Namespace '{namespace}' was not found (already removed)")
        else:
            if verbose:
                console.print(f"⚠️ Namespace removal warning: {result.stderr}")
    except Exception as e:
        raise RuntimeError(f"Failed to remove namespace: {str(e)}")


def kubectl_apply(yaml_content: str) -> bool:
    """Apply Kubernetes YAML content using kubectl.

    Args:
        yaml_content: YAML content to apply

    Returns:
        bool: True if successful, False if failed
    """
    try:
        subprocess.run(
            ["microk8s", "kubectl", "apply", "-f", "-"],
            input=yaml_content.encode("utf-8"),
            capture_output=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


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


def get_deployment_status(namespace: str, console: Console, verbose: bool = False) -> bool:
    """Check deployment status in a Kubernetes namespace.

    Args:
        namespace: Kubernetes namespace to check
        console: Console for output
        verbose: Whether to show verbose output

    Returns:
        bool: True if deployment status check succeeded, False otherwise
    """
    if verbose:
        console.print("[blue]ℹ[/blue] Checking deployment status...")

    try:
        # Check if namespace exists
        result = subprocess.run(
            ["microk8s", "kubectl", "get", "namespace", namespace],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            if verbose:
                console.print(f"[yellow]⚠[/yellow] Namespace '{namespace}' does not exist")
            return False

        # Check pods
        result = subprocess.run(
            ["microk8s", "kubectl", "get", "pods", "-n", namespace],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            console.print(result.stdout)
        else:
            if verbose:
                console.print("[red]✗[/red] Failed to get pod status")
            return False

        return True

    except Exception as e:
        if verbose:
            console.print(f"[red]✗[/red] Status check error: {str(e)}")
        return False


def _confirm_removal(
    release_name: str, namespace: str, force: bool, verbose: bool, console: Console
) -> bool:
    """Handle removal confirmation logic."""
    if not force:
        response = typer.confirm(
            f"Are you sure you want to remove deployment '{release_name}' from namespace '{namespace}'?"
        )
        if not response:
            if verbose:
                console.print("[blue]ℹ[/blue] Removal cancelled.")
            return False
    return True


def _remove_helm_release(
    release_name: str, namespace: str, verbose: bool, console: Console
) -> None:
    """Remove Helm release."""
    result = subprocess.run(
        ["microk8s", "helm", "uninstall", release_name, "-n", namespace],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        if verbose:
            console.print("[green]✓[/green] Release removed successfully!")
    else:
        if verbose:
            console.print("[yellow]⚠[/yellow] Helm release removal failed or was already removed")


def _cleanup_remaining_resources(namespace: str, verbose: bool, console: Console) -> None:
    """Clean up remaining Kubernetes resources in namespace."""
    if verbose:
        console.print("[blue]ℹ[/blue] Cleaning up remaining resources...")

    cleanup_commands = [
        [
            "microk8s",
            "kubectl",
            "delete",
            "pods",
            "--all",
            "-n",
            namespace,
            "--ignore-not-found",
        ],
        [
            "microk8s",
            "kubectl",
            "delete",
            "services",
            "--all",
            "-n",
            namespace,
            "--ignore-not-found",
        ],
        [
            "microk8s",
            "kubectl",
            "delete",
            "configmaps",
            "--all",
            "-n",
            namespace,
            "--ignore-not-found",
        ],
        [
            "microk8s",
            "kubectl",
            "delete",
            "secrets",
            "--all",
            "-n",
            namespace,
            "--ignore-not-found",
        ],
        [
            "microk8s",
            "kubectl",
            "delete",
            "persistentvolumeclaims",
            "--all",
            "-n",
            namespace,
            "--ignore-not-found",
        ],
    ]

    for cmd in cleanup_commands:
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            if verbose:
                console.print(f"[yellow]⚠[/yellow] Cleanup command timed out: {' '.join(cmd)}")
        except Exception:
            pass  # Ignore cleanup errors


def _remove_namespace(namespace: str, verbose: bool, console: Console) -> None:
    """Remove Kubernetes namespace."""
    if verbose:
        console.print(f"[blue]ℹ[/blue] Removing namespace '{namespace}'...")
    result = subprocess.run(
        [
            "microk8s",
            "kubectl",
            "delete",
            "namespace",
            namespace,
            "--ignore-not-found",
            "--timeout=60s",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        if verbose:
            console.print(f"[green]✓[/green] Namespace '{namespace}' removed successfully!")
    else:
        if verbose:
            console.print(
                f"[yellow]⚠[/yellow] Namespace '{namespace}' removal failed or was already removed"
            )


def remove_deployment(
    namespace: str,
    release_name: str,
    console: Console,
    verbose: bool = False,
    force: bool = False,
) -> bool:
    """Remove a deployment including Helm release, resources, and namespace.

    Args:
        namespace: Kubernetes namespace to remove
        release_name: Helm release name to remove
        console: Console for output
        verbose: Whether to show verbose output
        force: Whether to skip confirmation prompt

    Returns:
        bool: True if removal succeeded, False otherwise
    """
    # Handle confirmation
    if not _confirm_removal(release_name, namespace, force, verbose, console):
        return True

    if verbose:
        console.print("[blue]ℹ[/blue] Removing deployment...")

    try:
        # Remove Helm release
        _remove_helm_release(release_name, namespace, verbose, console)

        # Clean up remaining resources
        _cleanup_remaining_resources(namespace, verbose, console)

        # Remove namespace
        _remove_namespace(namespace, verbose, console)

        return True

    except Exception as e:
        if verbose:
            console.print(f"[red]✗[/red] Removal error: {str(e)}")
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
    from typing import List

    import yaml

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


def _load_dev_app_as_package(app_path: Path, app_name: str):
    """Load a dev app as a proper Python package with support for relative imports."""
    import types

    vantage_cli_module_name = f"vantage_cli.apps.{app_name}"

    # Ensure parent package exists for relative imports
    parent_package = "vantage_cli.apps"
    if parent_package not in sys.modules:
        parent_mod = types.ModuleType(parent_package)
        parent_mod.__path__ = []
        parent_mod.__package__ = parent_package
        sys.modules[parent_package] = parent_mod

    # Create the main package module with proper __path__ for relative imports
    package_module = types.ModuleType(vantage_cli_module_name)
    package_module.__path__ = [str(app_path)]  # This enables relative imports
    package_module.__package__ = vantage_cli_module_name
    sys.modules[vantage_cli_module_name] = package_module

    # Load all Python files as submodules
    app_module = None
    app_dir_path = str(app_path)

    for root, _, files in os.walk(app_dir_path):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                file_path = os.path.join(root, file)
                module_stem = file[:-3]  # Remove .py extension

                # Create full module name
                module_name = f"{vantage_cli_module_name}.{module_stem}"

                # Create and load the module
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    module.__package__ = (
                        vantage_cli_module_name  # Set package for relative imports
                    )
                    sys.modules[module_name] = module

                    # Set as attribute on package for dot notation access
                    setattr(package_module, module_stem, module)

                    # Execute the module
                    spec.loader.exec_module(module)

                    if file == "app.py":
                        app_module = module

    return app_module


def _discover_builtin_apps(built_in_apps_dir: Path) -> list[tuple]:
    """Discover built-in apps from the apps directory."""
    built_in_apps = []
    for app_path in built_in_apps_dir.iterdir():
        if app_path.is_dir() and not app_path.name.startswith("__"):
            app_module_path = app_path / "app.py"
            if app_module_path.exists():
                built_in_apps.append((app_path, True))  # (path, is_builtin)
    return built_in_apps


def _discover_dev_apps() -> list[tuple]:
    """Discover dev apps from the dev apps directory."""
    dev_apps = []
    if VANTAGE_CLI_DEV_APPS_DIR.exists():
        dev_apps_dir = VANTAGE_CLI_DEV_APPS_DIR / "apps"
        if dev_apps_dir.exists():
            # Add dev apps directory to Python path
            dev_apps_parent = str(VANTAGE_CLI_DEV_APPS_DIR)
            if dev_apps_parent not in sys.path:
                sys.path.insert(0, dev_apps_parent)

            # Sort dev apps to load keycloak before full (dependency order)
            app_paths = []
            for app_path in dev_apps_dir.iterdir():
                if app_path.is_dir() and not (
                    app_path.name.startswith("__") or app_path.name.startswith(".")
                ):
                    app_module_path = app_path / "app.py"
                    if app_module_path.exists():
                        app_paths.append(app_path)

            # Sort so keycloak comes before full
            app_paths.sort(key=lambda p: (0 if "keycloak" in p.name else 1, p.name))

            for app_path in app_paths:
                dev_apps.append((app_path, False))  # (path, is_builtin)
    return dev_apps


def _process_app(app_path: Path, is_builtin: bool, apps: Dict[str, Dict[str, Any]]) -> None:
    """Process a single app and add it to the apps dictionary."""
    app_name = app_path.name
    command_name = app_name.replace("_", "-")

    try:
        if is_builtin:
            # Import built-in app
            app_module = importlib.import_module(f"vantage_cli.apps.{app_name}.app")
        else:
            # Import dev app using direct file loading with proper package system
            app_module = None
            try:
                app_module = _load_dev_app_as_package(app_path, app_name)
                if app_module is None:
                    logger.warning(f"Could not load dev app '{app_name}'")
                    return

            except Exception as e:
                logger.warning(f"Failed to load dev app '{app_name}': {e}")
                return
    except ImportError as e:
        logger.warning(f"Failed to import app '{app_name}': {e}")
        return
    except Exception as e:
        logger.warning(f"Error loading app '{app_name}': {e}")
        return

    # Check if deploy function exists
    try:
        if hasattr(app_module, "deploy"):
            deploy_function = getattr(app_module, "deploy")
            # Use command_name (with hyphens) as key so CLI can find it
            apps[command_name] = {
                "module": app_module,
                "deploy_function": deploy_function,
            }
    except Exception as e:
        logger.error(f"Unexpected error processing app '{app_name}': {e}")
        logger.debug(f"Full traceback for {app_name}", exc_info=True)


def get_available_apps() -> Dict[str, Dict[str, Any]]:
    """Dynamically discover available deployment apps."""
    apps: Dict[str, Dict[str, Any]] = {}

    # Register the apps maintained with the vantage cli
    built_in_apps_dir = Path(__file__).parent

    if not built_in_apps_dir.exists():
        logging.warning(f"Apps directory not found: {built_in_apps_dir}")
        return apps

    # Discover built-in and dev apps
    built_in_apps = _discover_builtin_apps(built_in_apps_dir)
    dev_apps = _discover_dev_apps()

    # Combine and process all apps
    all_apps = built_in_apps + dev_apps
    for app_path, is_builtin in all_apps:
        _process_app(app_path, is_builtin, apps)

    return apps
