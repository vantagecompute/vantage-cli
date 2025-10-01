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
"""Deployment CRUD SDK that matches the deployment command interface."""

from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
import yaml
from loguru import logger

from vantage_cli.exceptions import Abort
from vantage_cli.sdk.deployment.schema import Deployment


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

    async def list(self, ctx: typer.Context, **kwargs: Any) -> List[Dict[str, Any]]:
        """List deployments with optional filtering.

        This method provides the interface expected by the deployment list command.

        Args:
            ctx: Typer context
            **kwargs: Filtering options like cloud, status, etc.

        Returns:
            List of deployment dictionaries with keys expected by commands:
            - deployment_id
            - deployment_name
            - app_name
            - cluster_name
            - cloud
            - created_at
            - status
        """
        deployments_data = self._load_deployments_data()
        all_deployments = deployments_data.get("deployments", {})

        # Convert to list format expected by the deployment commands
        deployments: List[Dict[str, Any]] = []
        for deployment_id, deployment_record in all_deployments.items():
            cluster_data = deployment_record.get("cluster_data", {})
            cluster_name = cluster_data.get(
                "name", deployment_record.get("cluster_name", "unknown")
            )

            # Handle inconsistent deployment_name field
            # Priority: deployment_name > name > fallback to "unknown"
            deployment_name = deployment_record.get("deployment_name") or deployment_record.get(
                "name", "unknown"
            )

            # Map the file structure to the command interface
            deployment: Dict[str, Any] = {
                "deployment_id": deployment_id,
                "deployment_name": deployment_name,
                "app_name": deployment_record.get("app_name", "unknown"),
                "cluster_name": cluster_name,
                "cloud": deployment_record.get("cloud", "unknown"),
                "created_at": deployment_record.get("created_at", "unknown"),
                "status": deployment_record.get("status", "unknown"),
                # Additional fields that might be useful
                "cluster_id": deployment_record.get("cluster_id", "unknown"),
                "cloud_type": deployment_record.get("cloud_type", "unknown"),
                "k8s_namespaces": deployment_record.get("k8s_namespaces", []),
                "metadata": deployment_record.get("metadata", {}),
                "cluster_data": cluster_data,
            }
            deployments.append(deployment)

        # Apply filters exactly as the command expects
        cloud_filter = kwargs.get("cloud")
        if cloud_filter and cloud_filter != "all":
            deployments = [
                d for d in deployments if d.get("cloud", "").lower() == cloud_filter.lower()
            ]

        status_filter = kwargs.get("status")
        if status_filter and status_filter != "all":
            deployments = [d for d in deployments if d.get("status") == status_filter]

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
        """Get a specific deployment by ID.

        Args:
            ctx: Typer context
            deployment_id: ID of the deployment to retrieve
            **kwargs: Additional parameters

        Returns:
            Deployment object or None if not found
        """
        deployments_data = self._load_deployments_data()
        all_deployments = deployments_data.get("deployments", {})

        if deployment_id not in all_deployments:
            return None

        deployment_record = all_deployments[deployment_id]
        cluster_data = deployment_record.get("cluster_data", {})
        cluster_name = cluster_data.get("name", deployment_record.get("cluster_name", "unknown"))

        # Handle inconsistent deployment_name field
        # Priority: deployment_name > name > fallback to "unknown"
        deployment_name = deployment_record.get("deployment_name") or deployment_record.get(
            "name", "unknown"
        )

        try:
            deployment = Deployment(
                deployment_id=deployment_id,
                deployment_name=deployment_name,
                app_name=deployment_record.get("app_name", "unknown"),
                cluster_name=cluster_name,
                cluster_id=deployment_record.get("cluster_id", "unknown"),
                cloud=deployment_record.get("cloud", "unknown"),
                created_at=deployment_record.get("created_at", "unknown"),
                status=deployment_record.get("status", "unknown"),
            )
            return deployment
        except Exception as e:
            logger.warning(f"Failed to parse deployment data for {deployment_id}: {e}")
            return None

    async def get_deployment_details(
        self, ctx: typer.Context, deployment_id: str, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        """Get detailed deployment data including all fields from the YAML file.

        Args:
            ctx: Typer context
            deployment_id: ID of the deployment to retrieve
            **kwargs: Additional parameters

        Returns:
            Complete deployment data dictionary or None if not found
        """
        deployments_data = self._load_deployments_data()
        all_deployments = deployments_data.get("deployments", {})

        if deployment_id not in all_deployments:
            return None

        deployment_record = all_deployments[deployment_id]
        cluster_data = deployment_record.get("cluster_data", {})
        cluster_name = cluster_data.get("name", deployment_record.get("cluster_name", "unknown"))

        # Handle inconsistent deployment_name field
        # Priority: deployment_name > name > fallback to "unknown"
        deployment_name = deployment_record.get("deployment_name") or deployment_record.get(
            "name", "unknown"
        )

        # Return complete deployment details
        details: Dict[str, Any] = {
            "deployment_id": deployment_id,
            "deployment_name": deployment_name,
            "app_name": deployment_record.get("app_name", "unknown"),
            "cluster_name": cluster_name,
            "cluster_id": deployment_record.get("cluster_id", "unknown"),
            "cloud": deployment_record.get("cloud", "unknown"),
            "cloud_type": deployment_record.get("cloud_type", "unknown"),
            "status": deployment_record.get("status", "unknown"),
            "created_at": deployment_record.get("created_at", "unknown"),
            "updated_at": deployment_record.get("updated_at", "unknown"),
            "k8s_namespaces": deployment_record.get("k8s_namespaces", []),
            "metadata": deployment_record.get("metadata", {}),
            "cluster_data": cluster_data,
            "client_id": deployment_record.get("client_id", "unknown"),
        }

        return details

    async def get(
        self, ctx: typer.Context, deployment_id: str, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        """Get a specific deployment by ID (convenience method).

        This is a convenience method that wraps get_deployment_details to provide
        a shorter method name for SDK usage.

        Args:
            ctx: Typer context
            deployment_id: ID of the deployment to retrieve
            **kwargs: Additional parameters

        Returns:
            Complete deployment data dictionary or None if not found
        """
        return await self.get_deployment_details(ctx, deployment_id, **kwargs)

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

    async def delete(self, ctx: typer.Context, deployment_id: str, **kwargs: Any) -> bool:
        """Delete a deployment.

        Args:
            ctx: Typer context
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


# Create the singleton instance
deployment_sdk = DeploymentSDK()
