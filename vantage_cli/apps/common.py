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

from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
import yaml
from rich.console import Console

from vantage_cli.apps.constants import (
    DEV_CLIENT_ID,
    DEV_CLIENT_SECRET,
    DEV_JUPYTERHUB_TOKEN,
    DEV_SSSD_BINDER_PASSWORD,
)
from vantage_cli.sdk.cluster.schema import Cluster, VantageClusterContext
from vantage_cli.sdk.deployment.schema import Deployment


def generate_default_deployment_name(app_name: str, cluster_name: str) -> str:
    """Generate a default deployment name from app name and cluster name.

    Args:
        app_name: Name of the application being deployed
        cluster_name: Name of the cluster

    Returns:
        Generated deployment name in format: {app_name}-{cluster_name}
    """
    return f"{app_name}-{cluster_name}"


def validate_client_credentials(cluster: Cluster, console: Console) -> tuple[str, Optional[str]]:
    """Validate and extract client credentials from cluster object.

    Args:
        cluster: Cluster object
        console: Rich console for error output

    Returns:
        Tuple of (client_id, client_secret) where client_secret may be None

    Raises:
        typer.Exit: If client_id is missing
    """
    client_id = cluster.client_id
    if not client_id:
        console.print("[bold red]✗ Missing client ID in cluster data[/bold red]")
        console.print("[dim]Client ID (clientId) is required for deployment[/dim]")
        raise typer.Exit(code=1)

    client_secret = cluster.client_secret
    return client_id, client_secret


def get_jupyterhub_token(cluster: Cluster) -> Optional[str]:
    """Return JupyterHub token from cluster object or None.

    Args:
        cluster: Cluster object

    Returns:
        JupyterHub token if available, otherwise None
    """
    return cluster.jupyterhub_token or None


def get_sssd_binder_password(cluster: Cluster) -> Optional[str]:
    """Return SSSD binder password from cluster object or None.

    Args:
        cluster: Cluster object

    Returns:
        SSSD binder password if available, otherwise None
    """
    return cluster.sssd_binder_password


def generate_dev_cluster_data(cluster_name: Optional[str] = None) -> Cluster:
    """Generate dummy cluster data for development/testing purposes.

    Args:
        cluster_name: Name of the cluster for development

    Returns:
        Cluster object containing dummy cluster data with all required fields
    """
    return Cluster(
        name=f"dev-cluster-{cluster_name or ''}",
        client_id=DEV_CLIENT_ID,
        client_secret=DEV_CLIENT_SECRET,
        status="dev",
        description=f"Development cluster {cluster_name or ''}",
        owner_email="dev@localhost",
        provider="dev",
        cloud_account_id=None,
        creation_parameters={
            "jupyterhub_token": DEV_JUPYTERHUB_TOKEN,
        },
        sssd_binder_password=DEV_SSSD_BINDER_PASSWORD,
    )


def get_deployments_file_path() -> Path:
    """Get the path to the deployments tracking file.

    Returns:
        Path to ~/.vantage-cli/deployments.yaml
    """
    vantage_dir = Path.home() / ".vantage-cli"
    vantage_dir.mkdir(exist_ok=True)
    return vantage_dir / "deployments.yaml"


def load_deployments() -> Dict[str, Any]:
    """Load deployment tracking data from ~/.vantage-cli/deployments.yaml.

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


def get_deployment_by_name(deployment_name: str) -> Optional[Deployment]:
    """Get deployment information by name.

    Args:
        deployment_name: Unique name for the deployment

    Returns:
        Normalized deployment record dictionary or None if not found
    """
    deployments_data = load_deployments()
    for deployment_data in deployments_data["deployments"].values():
        if deployment_data.get("name") == deployment_name:
            return Deployment(**deployment_data)
    return None


def get_deployment(deployment_id: str) -> Optional[Deployment]:
    """Get deployment information by ID.

    Args:
        deployment_id: Unique identifier for the deployment

    Returns:
        Normalized deployment record dictionary or None if not found
    """
    deployments_data = load_deployments()
    if deployment_data := deployments_data["deployments"].get(deployment_id):
        return Deployment(**deployment_data)
    return None


def get_deployments() -> List[Deployment]:
    """Get all deployments with their IDs included.

    Returns:
        List of deployment records with deployment_id field added and normalized
    """
    deployments = load_deployments()

    return [
        Deployment(**deployment_data) for deployment_data in deployments["deployments"].values()
    ]


def list_deployments_by_app(app_name: str) -> List[Deployment | Any]:
    """List all deployments for a specific app.

    Args:
        app_name: Name of the app to filter by

    Returns:
        List of deployment records for the specified app
    """
    deployments_data = load_deployments()
    return [
        Deployment(**deployment_data)
        for deployment_data in deployments_data["deployments"].values()
        if deployment_data.get("app_name") == app_name
    ]


def list_deployments_by_cluster(cluster_name: str) -> List[Deployment | Any]:
    """List all active deployments for a specific cluster.

    Args:
        cluster_name: Name of the cluster to filter by

    Returns:
        List of deployment records per cluster
    """
    deployments_data = load_deployments()
    return [
        Deployment(**deployment_data)
        for deployment_data in deployments_data["deployments"].values()
        if deployment_data.get("cluster_name") == cluster_name
        and deployment_data.get("status") == "active"
    ]


def create_deployment_with_init_status(
    app_name: str,
    cluster: Cluster,
    vantage_cluster_ctx: VantageClusterContext,
    cloud_provider: str,
    substrate: str,
    additional_metadata: Optional[Dict[str, Any]] = None,
    k8s_namespaces: Optional[List[str]] = None,
    verbose: bool = False,
) -> Deployment:
    """Create a new deployment with 'init' status immediately after dependency checks.

    Args:
        app_name: Name of the app being deployed (e.g., 'slurm-microk8s-localhost')
        cluster: Cluster object
        cloud_provider: Cloud provider type (e.g., 'localhost', 'aws', 'gcp')
        substrate: Cloud infrastructure type (e.g., 'k8s', 'vm', 'container')
        additional_metadata: Additional app-specific metadata to store
        k8s_namespaces: List of Kubernetes namespaces created by this deployment
        verbose: Whether to show verbose output
    """
    deployments_data = load_deployments()

    deployment = Deployment(
        app_name=app_name,
        cluster=cluster,
        vantage_cluster_ctx=vantage_cluster_ctx,
        cloud_provider=cloud_provider,
        substrate=substrate,
        status="init",
        k8s_namespaces=k8s_namespaces or [],
        additional_metadata=additional_metadata or {},
    )

    deployments_data["deployments"][f"{deployment.id}"] = deployment.model_dump()

    return deployment


def update_deployment_status(deployment_id: str, status: str, verbose: bool = False) -> bool:
    """Update the status of an existing deployment.

    Args:
        deployment_id: ID of the deployment to update
        status: New status value (e.g., 'active', 'failed', 'terminated')
        verbose: Whether to show verbose output

    Returns:
        True if update was successful, False if deployment not found
    """
    deployments_data = load_deployments()

    if deployment_id in deployments_data["deployments"]:
        deployments_data["deployments"][deployment_id]["status"] = status
        # Auto-update updated_at timestamp (handled by Deployment schema)
        save_deployments(deployments_data)
        return True
    return False


def remove_deployment(deployment_id: str) -> bool:
    """Remove a deployment entry completely from the tracking file.

    Args:
        deployment_id: Unique identifier for the deployment

    Returns:
        True if deployment was found and removed, False otherwise
    """
    deployments_data = load_deployments()
    if deployment_id in deployments_data["deployments"]:
        del deployments_data["deployments"][deployment_id]
        save_deployments(deployments_data)
        return True
    return False


def save_deployments(deployments_data: Dict[str, Any]) -> None:
    """Save deployment tracking data to ~/.vantage-cli/deployments.yaml.

    Args:
        deployments_data: Dictionary containing deployments data
    """
    deployments_file = get_deployments_file_path()
    try:
        with open(deployments_file, "w") as f:
            yaml.dump(deployments_data, f, default_flow_style=False, indent=2)
    except Exception:
        # Save failed - handled by higher level error handling
        pass
