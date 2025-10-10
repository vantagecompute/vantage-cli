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
"""Deployment CRUD SDK that uses the deployment command interface."""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import typer
import yaml
from loguru import logger

from vantage_cli.exceptions import Abort
from vantage_cli.sdk.deployment.schema import Deployment

if TYPE_CHECKING:
    from vantage_cli.sdk.cluster.schema import Cluster, VantageClusterContext


class DeploymentSDK:
    """SDK for deployment CRUD operations that matches the deployment command interface.

    This SDK reads from ~/.vantage-cli/deployments.yaml and provides the interface
    expected by the deployment commands.
    """

    def __init__(self):
        """Initialize the deployment SDK."""
        pass

    def _get_deployments_file_path(self) -> Path:
        """Get the path to the deployments file.

        Returns:
            Path to ~/.vantage-cli/deployments.yaml
        """
        vantage_dir = Path.home() / ".vantage-cli"
        vantage_dir.mkdir(exist_ok=True)
        return vantage_dir / "deployments.yaml"

    def _load_deployments_data(self) -> Dict[str, Any]:
        """Load deployment data from ~/.vantage-cli/deployments.yaml.

        Returns:
            Dictionary containing deployments data with 'deployments' key
        """
        deployments_file = self._get_deployments_file_path()
        if not deployments_file.exists():
            return {"deployments": {}}

        try:
            with open(deployments_file, "r") as f:
                data: Dict[str, Any] = yaml.safe_load(f) or {}
                # Ensure the structure exists
                if "deployments" not in data:
                    data["deployments"] = {}
                return data
        except Exception as e:
            logger.warning(f"Failed to load deployments file: {e}")
            return {"deployments": {}}

    def _save_deployments_data(self, deployments_data: Dict[str, Any]) -> None:
        """Save deployment data to ~/.vantage-cli/deployments.yaml.

        Args:
            deployments_data: Dictionary containing deployments data
        """
        deployments_file = self._get_deployments_file_path()
        try:
            with open(deployments_file, "w") as f:
                yaml.dump(deployments_data, f, default_flow_style=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save deployments file: {e}")
            raise Abort(f"Failed to save deployments: {e}")

    def _dict_to_deployment(
        self, deployment_id: str, deployment_data: Dict[str, Any]
    ) -> Optional[Deployment]:
        """Convert a dictionary from YAML to a Deployment object.

        Args:
            deployment_id: The deployment ID (UUID string)
            deployment_data: Dictionary containing deployment data from YAML

        Returns:
            Deployment object or None if conversion fails
        """
        try:
            from datetime import datetime
            from vantage_cli.sdk.cluster.schema import Cluster, VantageClusterContext

            # Parse datetime strings to datetime objects
            created_at = deployment_data.get("created_at")
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            elif not isinstance(created_at, datetime):
                created_at = datetime.now()

            updated_at = deployment_data.get("updated_at")
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at)
            elif updated_at is None:
                updated_at = created_at

            # Parse nested Cluster object
            cluster_data = deployment_data.get("cluster")
            if isinstance(cluster_data, dict):
                cluster = Cluster(**cluster_data)
            elif hasattr(cluster_data, "model_dump"):
                # Already a Cluster object
                cluster = cluster_data
            else:
                logger.warning(f"Missing or invalid cluster data for deployment {deployment_id}")
                return None

            # Parse nested VantageClusterContext object
            vantage_ctx_data = deployment_data.get("vantage_cluster_ctx")
            if isinstance(vantage_ctx_data, dict):
                vantage_cluster_ctx = VantageClusterContext(**vantage_ctx_data)
            elif hasattr(vantage_ctx_data, "model_dump"):
                # Already a VantageClusterContext object
                vantage_cluster_ctx = vantage_ctx_data
            else:
                logger.warning(f"Missing or invalid vantage_cluster_ctx data for deployment {deployment_id}")
                return None

            # Create Deployment object (id is a string)
            return Deployment(
                id=deployment_id,
                app_name=deployment_data.get("app_name", "unknown"),
                cluster=cluster,
                vantage_cluster_ctx=vantage_cluster_ctx,
                cloud_provider=deployment_data.get("cloud_provider", deployment_data.get("cloud", "unknown")),
                substrate=deployment_data.get("substrate", "unknown"),
                status=deployment_data.get("status", "unknown"),
                created_at=created_at,
                updated_at=updated_at,
                deployment_type=deployment_data.get("deployment_type"),
                k8s_namespaces=deployment_data.get("k8s_namespaces"),
                additional_metadata=deployment_data.get("metadata"),
            )
        except Exception as e:
            logger.warning(f"Failed to convert deployment {deployment_id} to Deployment object: {e}")
            return None

    async def list(self, ctx: typer.Context, **kwargs: Any) -> List[Deployment]:
        """List deployments with optional filtering.

        This method provides the interface expected by the deployment list command.

        Args:
            ctx: Typer context
            **kwargs: Filtering options like cloud, status, etc.

        Returns:
            List of Deployment objects
        """
        deployments_data = self._load_deployments_data()
        all_deployments = deployments_data.get("deployments", {})

        # Convert to Deployment objects
        deployments: List[Deployment] = []
        for deployment_id, deployment_record in all_deployments.items():
            # Use the helper method to convert dict to Deployment object
            deployment = self._dict_to_deployment(deployment_id, deployment_record)
            if deployment:
                deployments.append(deployment)

        # Apply filters
        cloud_filter = kwargs.get("cloud")
        if cloud_filter and cloud_filter != "all":
            deployments = [
                d for d in deployments if d.cloud_provider.lower() == cloud_filter.lower()
            ]

        status_filter = kwargs.get("status")
        if status_filter and status_filter != "all":
            deployments = [d for d in deployments if d.status == status_filter]

        logger.debug(f"Returning {len(deployments)} deployments after filtering")
        return deployments

    async def list_deployments(self, ctx: typer.Context, **kwargs: Any) -> List[Deployment]:
        """List deployments as Deployment objects for the dashboard.

        Args:
            ctx: Typer context
            **kwargs: Additional filtering parameters

        Returns:
            List of Deployment objects
        """
        # Get raw deployment data from the base list method
        deployments_raw = await self.list(ctx, **kwargs)

        deployments: List[Deployment] = []
        for deployment_data in deployments_raw:
            try:
                deployment = Deployment(
                    deployment_id=deployment_data.get("deployment_id", ""),
                    deployment_name=deployment_data.get("deployment_name", "unknown"),
                    app_name=deployment_data.get("app_name", "unknown"),
                    cluster_name=deployment_data.get("cluster_name", "unknown"),
                    cluster_id=deployment_data.get("cluster_id", "unknown"),
                    cloud=deployment_data.get("cloud", "unknown"),
                    created_at=deployment_data.get("created_at", "unknown"),
                    status=deployment_data.get("status", "unknown"),
                )
                deployments.append(deployment)
            except Exception as e:
                logger.warning(f"Failed to parse deployment data: {e}")
                continue

        return deployments

    async def get_deployment(
        self, ctx: typer.Context, deployment_id: str, **kwargs: Any
    ) -> Optional[Deployment]:
        """Get detailed deployment data as a Deployment object.

        Args:
            ctx: Typer context
            deployment_id: ID of the deployment to retrieve

        Returns:
            Deployment object or None if not found
        """
        deployments_data = self._load_deployments_data()
        all_deployments = deployments_data.get("deployments", {})

        if deployment_id not in all_deployments:
            return None

        deployment_record = all_deployments[deployment_id]
        
        # Use the helper method to convert dict to Deployment object
        return self._dict_to_deployment(deployment_id, deployment_record)

    async def get(
        self, ctx: typer.Context, deployment_id: str, **kwargs: Any
    ) -> Optional[Deployment]:
        """Get a specific deployment by ID (convenience method).

        This is a convenience method that wraps get_deployment_details to provide
        a shorter method name for SDK usage.

        Args:
            ctx: Typer context
            deployment_id: ID of the deployment to retrieve
            **kwargs: Additional parameters (unused currently)

        Returns:
            Deployment object or None if not found
        """
        return await self.get_deployment(ctx, deployment_id, **kwargs)

    async def update_deployment_status(
        self, ctx: typer.Context, deployment_id: str, status: str, **kwargs: Any
    ) -> bool:
        """Update the status of a deployment.

        Args:
            ctx: Typer context
            deployment_id: ID of the deployment to update
            status: New status value
            **kwargs: Additional parameters

        Returns:
            True if successful, False otherwise
        """
        deployments_data = self._load_deployments_data()
        all_deployments = deployments_data.get("deployments", {})

        if deployment_id not in all_deployments:
            logger.warning(f"Deployment {deployment_id} not found for status update")
            return False

        all_deployments[deployment_id]["status"] = status
        self._save_deployments_data(deployments_data)

        logger.info(f"Updated deployment '{deployment_id}' status to '{status}'")
        return True

    def create_deployment(
        self,
        app_name: str,
        cluster: "Cluster",
        vantage_cluster_ctx: "VantageClusterContext",
        cloud_provider: str,
        substrate: str,
        status: str = "init",
        additional_metadata: Optional[Dict[str, Any]] = None,
        k8s_namespaces: Optional[List[str]] = None,
        verbose: bool = False,
    ) -> Deployment:
        """Create a new deployment and save it to the deployments file.

        Args:
            app_name: Name of the app being deployed (e.g., 'slurm-multipass')
            cluster: Cluster object
            vantage_cluster_ctx: VantageClusterContext object
            cloud_provider: Cloud provider type (e.g., 'localhost', 'aws', 'gcp')
            substrate: Cloud infrastructure type (e.g., 'k8s', 'vm', 'container')
            status: Initial status (default: 'init')
            additional_metadata: Additional app-specific metadata to store
            k8s_namespaces: List of Kubernetes namespaces created by this deployment
            verbose: Whether to show verbose output

        Returns:
            Deployment object
        """

        # Create the Deployment object (it will auto-generate an ID)
        deployment = Deployment(
            app_name=app_name,
            cluster=cluster,
            vantage_cluster_ctx=vantage_cluster_ctx,
            cloud_provider=cloud_provider,
            substrate=substrate,
            status=status,
            k8s_namespaces=k8s_namespaces or [],
            additional_metadata=additional_metadata or {},
        )

        # Save to file using the deployment's write method
        deployment.write()

        if verbose:
            logger.debug(f"Created deployment '{deployment.id}' for app '{app_name}' on cluster '{cluster.name}'")

        return deployment

    async def delete(self, deployment_id: str) -> bool:
        """Delete a deployment.

        Args:
            deployment_id: ID of the deployment to delete
            **kwargs: Additional parameters

        Returns:
            True if successful, False otherwise
        """
        deployments_data = self._load_deployments_data()
        all_deployments = deployments_data.get("deployments", {})

        if deployment_id not in all_deployments:
            logger.warning(f"Deployment {deployment_id} not found for deletion")
            return False

        del all_deployments[deployment_id]
        self._save_deployments_data(deployments_data)

        logger.info(f"Deleted deployment '{deployment_id}'")
        return True

    async def get_deployments_by_cluster(
        self, ctx: typer.Context, cluster_name: str
    ) -> List[Deployment]:
        """Get all deployments for a specific cluster.

        Args:
            ctx: The typer context object
            cluster_name: Name of the cluster

        Returns:
            List of Deployment objects for the cluster
        """
        all_deployments = await self.list(ctx)
        return [d for d in all_deployments if d.cluster.name == cluster_name]


# Create the singleton instance
deployment_sdk = DeploymentSDK()
