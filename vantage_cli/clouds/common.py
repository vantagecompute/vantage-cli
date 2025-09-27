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

from typing import Any, Dict, List, Optional

from vantage_cli.clouds.constants import (
    DEV_CLIENT_ID,
    DEV_CLIENT_SECRET,
    DEV_JUPYTERHUB_TOKEN,
    DEV_SSSD_BINDER_PASSWORD,
)
from vantage_cli.sdk.cloud.schema import Cloud
from vantage_cli.sdk.cloud_credential.schema import CloudCredential
from vantage_cli.sdk.cluster.schema import Cluster, VantageClusterContext
from vantage_cli.sdk.deployment.crud import deployment_sdk
from vantage_cli.sdk.deployment.schema import Deployment


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


def create_deployment_with_init_status(
    app_name: str,
    cluster: Cluster,
    vantage_cluster_ctx: VantageClusterContext,
    cloud: Cloud,
    substrate: str,
    credential: Optional[CloudCredential] = None,
    additional_metadata: Optional[Dict[str, Any]] = None,
    k8s_namespaces: Optional[List[str]] = None,
    verbose: bool = False,
) -> Deployment:
    """Create a new deployment with 'init' status immediately after dependency checks.

    Args:
        app_name: Name of the app being deployed (e.g., 'slurm-microk8s-localhost')
        cluster: Cluster object
        vantage_cluster_ctx: Context containing cluster configuration and state
        cloud: Cloud provider configuration object
        substrate: Cloud infrastructure type (e.g., 'k8s', 'vm', 'container')
        credential: Optional cloud provider credentials
        additional_metadata: Additional app-specific metadata to store
        k8s_namespaces: List of Kubernetes namespaces created by this deployment
        verbose: Whether to show verbose output
    """
    return deployment_sdk.create_deployment(
        app_name=app_name,
        cluster=cluster,
        vantage_cluster_ctx=vantage_cluster_ctx,
        cloud=cloud,
        credential=credential,
        substrate=substrate,
        status="init",
        additional_metadata=additional_metadata or {},
        k8s_namespaces=k8s_namespaces or [],
        verbose=verbose,
    )
