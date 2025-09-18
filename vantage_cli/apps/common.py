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

import typer
import yaml
from rich.console import Console

from vantage_cli.constants import (
    ERROR_NO_CLIENT_ID,
    ERROR_NO_CLIENT_SECRET,
    ERROR_NO_CLUSTER_DATA,
)


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
        console.print(ERROR_NO_CLUSTER_DATA)
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
        console.print(ERROR_NO_CLIENT_ID)
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
        console.print(ERROR_NO_CLIENT_SECRET)
        raise typer.Exit(code=1)
    return client_secret


def generate_dev_cluster_data(cluster_name: str) -> Dict[str, Any]:
    """Generate dummy cluster data for development/testing purposes.

    Args:
        cluster_name: Name of the cluster for development

    Returns:
        Dictionary containing dummy cluster data with all required fields
    """
    return {
        "name": cluster_name,
        "clientId": "dev-client-12345-abcde-fghij-klmno",
        "clientSecret": "dev-secret-67890-pqrst-uvwxy-zabcd",
        "creationParameters": {"jupyterhub_token": "dev-jupyter-token-98765"},
        # Additional dummy metadata
        "id": f"dev-cluster-{cluster_name}",
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
    except Exception as e:
        console.print(f"[yellow]Warning: Could not load deployments file: {e}[/yellow]")
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
    except Exception as e:
        console.print(f"[red]Error: Could not save deployments file: {e}[/red]")


def track_deployment(
    deployment_id: str,
    app_name: str,
    cluster_name: str,
    cluster_data: Dict[str, Any],
    console: Console,
    deployment_name: Optional[str] = None,
    additional_metadata: Optional[Dict[str, Any]] = None,
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
    """
    deployments_data = load_deployments(console)

    deployment_record = {
        "deployment_name": deployment_name or f"{app_name}-{cluster_name}",
        "app_name": app_name,
        "cluster_name": cluster_name,
        "cluster_id": cluster_data.get("id", "unknown"),
        "client_id": cluster_data.get("clientId", "unknown"),
        "created_at": datetime.now().isoformat(),
        "status": "active",
        "cluster_data": cluster_data,  # Store full cluster_data for cleanup
        "metadata": additional_metadata or {},
    }

    deployments_data["deployments"][deployment_id] = deployment_record
    save_deployments(deployments_data, console)

    console.print(
        f"[green]✓ Deployment '{deployment_id}' tracked in ~/.vantage-cli/deployments.yaml[/green]"
    )


def get_deployment(deployment_id: str, console: Console) -> Optional[Dict[str, Any]]:
    """Get deployment information by ID.

    Args:
        deployment_id: Unique identifier for the deployment
        console: Rich console for error output

    Returns:
        Deployment record dictionary or None if not found
    """
    deployments_data = load_deployments(console)
    return deployments_data["deployments"].get(deployment_id)


def get_deployments(console: Console) -> List[Dict[str, Any]]:
    """Get all deployments with their IDs included.

    Args:
        console: Rich console for error output

    Returns:
        List of deployment records with deployment_id field added
    """
    deployments_data = load_deployments(console)
    deployments_list = []

    for deployment_id, deployment_data in deployments_data["deployments"].items():
        # Add the deployment_id to the deployment data
        deployment_record = deployment_data.copy()
        deployment_record["deployment_id"] = deployment_id
        # Add cluster_data for cleanup functions (stored as metadata in old format)
        if "cluster_data" not in deployment_record and "metadata" in deployment_record:
            deployment_record["cluster_data"] = deployment_record["metadata"]
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
