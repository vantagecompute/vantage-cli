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
"""Common validation utilities for deployment apps."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import snick
import typer
import yaml
from rich.console import Console
from rich.panel import Panel

from vantage_cli.exceptions import Abort


def validate_cluster_data(
    cluster_data: Optional[Dict[str, Any]], console: Console
) -> Dict[str, Any]:
    """Validate that cluster data exists and contains required fields.

    Args:
        cluster_data: Optional cluster configuration dictionary
        console: Rich console for error output

    Returns:
        Validated cluster data dictionary

    Raises:
        typer.Exit: If validation fails
    """
    if not cluster_data:
        # Error handled by deployment progress renderer
        raise typer.Exit(code=1)
    return cluster_data


def validate_client_credentials(
    cluster_data: Dict[str, Any], console: Console
) -> tuple[str, Optional[str]]:
    """Validate and extract client credentials from cluster data.

    Args:
        cluster_data: Cluster configuration dictionary
        console: Rich console for error output

    Returns:
        Tuple of (client_id, client_secret) where client_secret may be None

    Raises:
        typer.Exit: If client_id is missing
    """
    client_id = cluster_data.get("clientId", None)
    if not client_id:
        # Error handled by deployment progress renderer
        raise typer.Exit(code=1)

    client_secret = cluster_data.get("clientSecret", None)
    return client_id, client_secret


def require_client_secret(client_secret: Optional[str], console: Console) -> str:
    """Validate that client secret exists.

    Args:
        client_secret: Optional client secret string
        console: Rich console for error output

    Returns:
        Validated client secret string

    Raises:
        typer.Exit: If client secret is missing
    """
    if not client_secret:
        # Error handled by deployment progress renderer
        raise typer.Exit(code=1)
    return client_secret


def render_user_help(
    title: str,
    problem_description: str,
    solutions: List[Dict[str, Any]],
    additional_notes: Optional[List[str]] = None,
    subject: Optional[str] = None,
    log_message: Optional[str] = None,
) -> None:
    """Render standardized user help messages for deployment issues.

    Args:
        title: Main title/heading for the help message
        problem_description: Description of the problem or missing requirement
        solutions: List of solution steps, each containing:
            - title: Step title/description
            - command: Command to run (optional)
            - note: Additional note about the step (optional)
        additional_notes: Optional list of additional notes to append
        subject: Subject for the Abort exception (defaults to title)
        log_message: Log message for the Abort exception (defaults to title)

    Raises:
        Abort: Always raises with formatted help message

    Example:
        render_user_help(
            title="MicroK8s Required",
            problem_description="MicroK8s not found. Please install MicroK8s first.",
            solutions=[
                {
                    "title": "Install MicroK8s",
                    "command": "sudo snap install microk8s --channel 1.29/stable --classic"
                },
                {
                    "title": "Enable required addons",
                    "command": "sudo microk8s.enable hostpath-storage dns metallb:10.64.140.43-10.64.140.49",
                    "note": "Adjust the MetalLB IP range to match your network"
                }
            ],
            additional_notes=["Ensure you have sudo privileges for installation"]
        )
    """
    message_parts = [f"• {problem_description}", ""]

    for solution in solutions:
        solution_title = solution.get("title", "")
        command = solution.get("command")
        note = solution.get("note")

        if solution_title:
            message_parts.append(f"• {solution_title}:")
        if command:
            message_parts.append(f"  {command}")
        if note:
            message_parts.append(f"  Note: {note}")
        message_parts.append("")

    if additional_notes:
        for note in additional_notes:
            message_parts.append(f"• {note}")
        message_parts.append("")

    # Remove trailing empty line
    if message_parts and message_parts[-1] == "":
        message_parts.pop()

    formatted_message = snick.dedent("\n".join(message_parts)).strip()

    # Create Rich Panel similar to render_quick_start_guide
    console = Console()
    panel = Panel(
        formatted_message,
        title=f"[bold red]{title}[/bold red]",
        border_style="red",
        expand=False,
    )

    console.print()
    console.print(panel)

    raise Abort(
        "",  # Empty message since we already displayed the Rich Panel
        subject=subject or title,
        log_message=log_message or title,
    )


def generate_dev_cluster_data(cluster_name: Optional[str] = None) -> Dict[str, Any]:
    """Generate dummy cluster data for development/testing purposes.

    Args:
        cluster_name: Name of the cluster for development

    Returns:
        Dictionary containing dummy cluster data with all required fields
    """
    return {
        "name": f"dev-cluster{cluster_name or ''}",
        "clientId": "dev-client-12345-abcde-fghij-klmno",
        "clientSecret": "dev-secret-67890-pqrst-uvwxy-zabcd",
        "creationParameters": {"jupyterhub_token": "dev-jupyter-token-98765"},
        # Additional dummy metadata
        "id": f"dev-cluster{cluster_name or ''}",
        "status": "dev",
        "region": "localhost",
        "provider": "dev",
    }


def generate_default_deployment_name(app_name: str, cluster_name: str) -> str:
    """Generate a default deployment name with timestamp.

    Args:
        app_name: Name of the app being deployed
        cluster_name: Name of the cluster

    Returns:
        Default deployment name in format: <app-name>-<cluster-name>-<timestamp-string>
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{app_name}-{cluster_name}-{timestamp}"


def get_deployments_file_path() -> Path:
    """Get the path to the deployments tracking file.

    Returns:
        Path to ~/.vantage-cli/deployments.yaml
    """
    vantage_dir = Path.home() / ".vantage-cli"
    vantage_dir.mkdir(exist_ok=True)
    return vantage_dir / "deployments.yaml"


def load_deployments(console: Console) -> Dict[str, Any]:
    """Load deployment tracking data from ~/.vantage-cli/deployments.yaml.

    Args:
        console: Rich console for warning output

    Returns:
        Dictionary containing deployments data with 'deployments' key
    """
    deployments_file = get_deployments_file_path()
    if not deployments_file.exists():
        return {"deployments": {}}

    try:
        with open(deployments_file, "r") as f:
            data = yaml.safe_load(f) or {}
            # Ensure the structure exists
            if "deployments" not in data:
                data["deployments"] = {}
            return data
    except Exception:
        # Load deployments and return empty dict with defaults on error
        return {"deployments": {}}


def save_deployments(deployments_data: Dict[str, Any], console: Console) -> None:
    """Save deployment tracking data to ~/.vantage-cli/deployments.yaml.

    Args:
        deployments_data: Dictionary containing deployments data
        console: Rich console for error output
    """
    deployments_file = get_deployments_file_path()
    try:
        with open(deployments_file, "w") as f:
            yaml.dump(deployments_data, f, default_flow_style=False, indent=2)
    except Exception:
        # Save failed - handled by higher level error handling
        pass


def track_deployment(
    deployment_id: str,
    app_name: str,
    cluster_name: str,
    cluster_data: Dict[str, Any],
    console: Console,
    deployment_name: Optional[str] = None,
    additional_metadata: Optional[Dict[str, Any]] = None,
    cloud: Optional[str] = None,
    cloud_type: Optional[str] = None,
    k8s_namespaces: Optional[List[str]] = None,
) -> None:
    """Track a new deployment in the deployments file.

    Args:
        deployment_id: Unique identifier for the deployment
        app_name: Name of the app being deployed (e.g., 'slurm-microk8s-localhost')
        cluster_name: Name of the cluster
        cluster_data: Cluster configuration data
        console: Rich console for output
        deployment_name: Human-readable name for the deployment (optional)
        additional_metadata: Additional app-specific metadata to store
        cloud: Cloud provider type (e.g., 'localhost', 'aws', 'gcp')
        cloud_type: Cloud infrastructure type (e.g., 'k8s', 'vm', 'container')
        k8s_namespaces: List of Kubernetes namespaces created by this deployment
    """
    deployments_data = load_deployments(console)

    # Extract cloud from cluster_data if not provided and available
    if cloud is None:
        cloud = cluster_data.get("cloud", "unknown")

    deployment_record = {
        "deployment_name": deployment_name or f"{app_name}-{cluster_name}",
        "app_name": app_name,
        "cluster_name": cluster_name,
        "cluster_id": cluster_data.get("id", "unknown"),
        "client_id": cluster_data.get("clientId", "unknown"),
        "cloud": cloud,
        "created_at": datetime.now().isoformat(),
        "status": "active",
        "cluster_data": cluster_data,  # Store full cluster_data for cleanup
        "metadata": additional_metadata or {},
    }

    deployments_data["deployments"][deployment_id] = deployment_record
    save_deployments(deployments_data, console)

    # Tracking message removed - handled by deployment progress renderer


def get_deployment(deployment_id: str, console: Console) -> Optional[Dict[str, Any]]:
    """Get deployment information by ID.

    Args:
        deployment_id: Unique identifier for the deployment
        console: Rich console for error output

    Returns:
        Normalized deployment record dictionary or None if not found
    """
    deployments_data = load_deployments(console)
    deployment_data = deployments_data["deployments"].get(deployment_id)

    if deployment_data is None:
        return None

    return normalize_deployment_data(deployment_id, deployment_data)


def get_deployment_field(
    deployment_data: Dict[str, Any], field: str, default: Any = "unknown"
) -> Any:
    """Get a deployment field with backward compatibility.

    Args:
        deployment_data: Deployment data dictionary
        field: Field name to retrieve
        default: Default value if field not found

    Returns:
        Field value or default
    """
    # Handle new field names
    if field == "name":
        return deployment_data.get("name") or deployment_data.get("deployment_name", default)
    elif field == "cluster_name":
        # Extract from cluster_data or use legacy field
        cluster_data = deployment_data.get("cluster_data", {})
        return cluster_data.get("name") or deployment_data.get("cluster_name", default)
    else:
        return deployment_data.get(field, default)


def normalize_deployment_data(
    deployment_id: str, deployment_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Normalize deployment data to include both old and new field formats for compatibility.

    Args:
        deployment_id: The deployment ID
        deployment_data: Raw deployment data

    Returns:
        Normalized deployment data with all required fields
    """
    normalized = deployment_data.copy()

    # Add deployment_id if not present
    if "deployment_id" not in normalized:
        normalized["deployment_id"] = deployment_id

    # Ensure backward compatibility fields exist
    if "deployment_name" not in normalized and "name" in normalized:
        normalized["deployment_name"] = normalized["name"]
    elif "name" not in normalized and "deployment_name" in normalized:
        normalized["name"] = normalized["deployment_name"]

    # Extract cluster_name from cluster_data if needed
    if "cluster_name" not in normalized:
        cluster_data = normalized.get("cluster_data", {})
        cluster_name = cluster_data.get("name", "unknown")
        normalized["cluster_name"] = cluster_name

    return normalized


def get_deployments(console: Console) -> List[Dict[str, Any]]:
    """Get all deployments with their IDs included.

    Args:
        console: Rich console for error output

    Returns:
        List of deployment records with deployment_id field added and normalized
    """
    deployments_data = load_deployments(console)
    deployments_list = []

    for deployment_id, deployment_data in deployments_data["deployments"].items():
        # Normalize deployment data for backward compatibility
        deployment_record = normalize_deployment_data(deployment_id, deployment_data)
        deployments_list.append(deployment_record)

    return deployments_list


def list_deployments_by_app(app_name: str, console: Console) -> Dict[str, Dict[str, Any]]:
    """List all deployments for a specific app.

    Args:
        app_name: Name of the app to filter by
        console: Rich console for error output

    Returns:
        Dictionary of deployment_id -> deployment_record
    """
    deployments_data = load_deployments(console)
    return {
        dep_id: dep_data
        for dep_id, dep_data in deployments_data["deployments"].items()
        if dep_data.get("app_name") == app_name and dep_data.get("status") == "active"
    }


def list_deployments_by_cluster(cluster_name: str, console: Console) -> Dict[str, Dict[str, Any]]:
    """List all active deployments for a specific cluster.

    Args:
        cluster_name: Name of the cluster to filter by
        console: Rich console for error output

    Returns:
        Dictionary of deployment_id -> deployment_record for active deployments
    """
    deployments_data = load_deployments(console)
    return {
        dep_id: dep_data
        for dep_id, dep_data in deployments_data["deployments"].items()
        if dep_data.get("cluster_name") == cluster_name and dep_data.get("status") == "active"
    }


def mark_deployment_deleted(deployment_id: str, console: Console) -> bool:
    """Mark a deployment as deleted in the tracking file.

    Args:
        deployment_id: Unique identifier for the deployment
        console: Rich console for error output

    Returns:
        True if deployment was found and marked as deleted, False otherwise
    """
    deployments_data = load_deployments(console)
    if deployment_id in deployments_data["deployments"]:
        deployments_data["deployments"][deployment_id]["status"] = "deleted"
        deployments_data["deployments"][deployment_id]["deleted_at"] = datetime.now().isoformat()
        save_deployments(deployments_data, console)
        return True
    return False


def create_deployment_with_init_status(
    deployment_id: str,
    app_name: str,
    cluster_name: str,
    cluster_data: Dict[str, Any],
    console: Console,
    deployment_name: Optional[str] = None,
    additional_metadata: Optional[Dict[str, Any]] = None,
    verbose: bool = False,
    cloud: Optional[str] = None,
    cloud_type: Optional[str] = None,
    k8s_namespaces: Optional[List[str]] = None,
) -> None:
    """Create a new deployment with 'init' status immediately after dependency checks.

    Args:
        deployment_id: Unique identifier for the deployment
        app_name: Name of the app being deployed (e.g., 'slurm-microk8s-localhost')
        cluster_name: Name of the cluster
        cluster_data: Cluster configuration data
        console: Rich console for output
        deployment_name: Human-readable name for the deployment (optional)
        additional_metadata: Additional app-specific metadata to store
        verbose: Whether to show verbose output
        cloud: Cloud provider type (e.g., 'localhost', 'aws', 'gcp')
        cloud_type: Cloud infrastructure type (e.g., 'k8s', 'vm', 'container')
        k8s_namespaces: List of Kubernetes namespaces created by this deployment
    """
    deployments_data = load_deployments(console)

    # Extract cloud from cluster_data if not provided and available
    if cloud is None:
        cloud = cluster_data.get("cloud", "unknown")

    deployment_record = {
        "name": deployment_name or f"{app_name}-{cluster_name}",
        "app_name": app_name,
        "cluster_id": cluster_data.get("id", "unknown"),
        "cloud": cloud,
        "cloud_type": cloud_type,
        "k8s_namespaces": k8s_namespaces or [],
        "status": "init",  # Start with init status
        "created_at": datetime.now().isoformat(),
        "cluster_data": cluster_data,  # Store full cluster_data for cleanup
        "metadata": additional_metadata or {},
    }

    deployments_data["deployments"][deployment_id] = deployment_record
    save_deployments(deployments_data, console)

    # Status creation message removed - handled by deployment progress renderer


def update_deployment_status(
    deployment_id: str, status: str, console: Console, verbose: bool = False
) -> bool:
    """Update the status of an existing deployment.

    Args:
        deployment_id: Unique identifier for the deployment
        status: New status (e.g., 'active', 'failed', 'init')
        console: Rich console for output
        verbose: Whether to enable verbose output

    Returns:
        True if deployment was found and updated, False otherwise
    """
    deployments_data = load_deployments(console)
    if deployment_id in deployments_data["deployments"]:
        deployments_data["deployments"][deployment_id]["status"] = status
        deployments_data["deployments"][deployment_id]["updated_at"] = datetime.now().isoformat()
        save_deployments(deployments_data, console)
        # Status update message removed - handled by deployment progress renderer
        return True
    else:
        # Error message removed - handled by deployment progress renderer
        return False


def remove_deployment(deployment_id: str, console: Console) -> bool:
    """Remove a deployment entry completely from the tracking file.

    Args:
        deployment_id: Unique identifier for the deployment
        console: Rich console for error output

    Returns:
        True if deployment was found and removed, False otherwise
    """
    deployments_data = load_deployments(console)
    if deployment_id in deployments_data["deployments"]:
        del deployments_data["deployments"][deployment_id]
        save_deployments(deployments_data, console)
        return True
    return False


def add_k8s_namespace_to_deployment(
    deployment_id: str, namespace: str, console: Console, verbose: bool = False
) -> bool:
    """Add a Kubernetes namespace to the deployment's k8s_namespaces list.

    Args:
        deployment_id: Unique identifier for the deployment
        namespace: Kubernetes namespace to add
        console: Rich console for output
        verbose: Whether to show verbose output

    Returns:
        True if namespace was added, False if deployment not found
    """
    deployments_data = load_deployments(console)
    if deployment_id in deployments_data["deployments"]:
        deployment = deployments_data["deployments"][deployment_id]

        # Initialize k8s_namespaces if it doesn't exist (for backward compatibility)
        if "k8s_namespaces" not in deployment:
            deployment["k8s_namespaces"] = []

        # Add namespace if not already in the list
        if namespace not in deployment["k8s_namespaces"]:
            deployment["k8s_namespaces"].append(namespace)
            save_deployments(deployments_data, console)

            # Namespace tracking messages removed - handled by deployment progress renderer
        # Namespace already tracked message removed - handled by deployment progress renderer

        return True
    else:
        # Deployment not found message removed - handled by deployment progress renderer
        return False


def get_k8s_namespaces_for_deployment(deployment_id: str, console: Console) -> List[str]:
    """Get the list of Kubernetes namespaces for a deployment.

    Args:
        deployment_id: Unique identifier for the deployment
        console: Rich console for error output

    Returns:
        List of Kubernetes namespaces, or empty list if deployment not found
    """
    deployments_data = load_deployments(console)
    if deployment_id in deployments_data["deployments"]:
        deployment = deployments_data["deployments"][deployment_id]
        return deployment.get("k8s_namespaces", [])
    return []
