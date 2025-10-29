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
"""Deployment schemas for the Vantage CLI."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import yaml
from pydantic import BaseModel, Field, computed_field

from vantage_cli.constants import VANTAGE_CLI_DEPLOYMENTS_YAML_PATH as DEPLOYMENTS_YAML
from vantage_cli.sdk.cloud.schema import Cloud
from vantage_cli.sdk.cloud_credential.schema import CloudCredential
from vantage_cli.sdk.cluster.schema import Cluster, VantageClusterContext


def load_deployments() -> Dict[str, Any]:
    """Load deployment tracking data from ~/.vantage-cli/deployments.yaml.

    Returns:
        Dictionary containing deployments data with 'deployments' key
    """
    if not DEPLOYMENTS_YAML.exists():
        return {"deployments": {}}

    try:
        data = yaml.safe_load(DEPLOYMENTS_YAML.read_text())
        if "deployments" not in data:
            data["deployments"] = {}
        return data
    except Exception:
        # Load deployments and return empty dict with defaults on error
        return {"deployments": {}}


def save_deployments(deployments_data: Dict[str, Any]) -> None:
    """Save deployment tracking data to ~/.vantage-cli/deployments.yaml.

    Args:
        deployments_data: Dictionary containing deployments data
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Ensure the directory exists
        DEPLOYMENTS_YAML.parent.mkdir(parents=True, exist_ok=True)
        DEPLOYMENTS_YAML.write_text(
            yaml.dump(deployments_data, default_flow_style=False, indent=2)
        )
    except Exception as e:
        logger.error(f"Failed to save deployments to {DEPLOYMENTS_YAML}: {e}")
        raise RuntimeError(f"Failed to save deployments: {e}") from e


class Deployment(BaseModel):
    """Schema for deployment data.

    The updated_at field is automatically refreshed whenever any field
    in the model is modified (e.g., deployment.status = "active").
    This happens transparently without requiring any user action.
    """

    model_config = {"validate_assignment": True}

    id: str = Field(default_factory=lambda: str(uuid4()))
    app_name: str
    cluster: Cluster
    vantage_cluster_ctx: VantageClusterContext
    cloud: Cloud
    credential: Optional[CloudCredential] = None
    substrate: str
    status: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

    # Additional fields that might be present
    deployment_type: Optional[str] = None
    k8s_namespaces: Optional[List[str]] = None
    additional_metadata: Optional[Dict[str, Any]] = None

    def __setattr__(self, name: str, value: Any) -> None:
        """Override setattr to auto-update updated_at when any field changes.

        This ensures that whenever a field is modified (e.g., deployment.status = "active"),
        the updated_at timestamp is automatically refreshed.
        """
        # Call parent setattr first
        super().__setattr__(name, value)

        # Auto-update updated_at for any field change except updated_at itself
        # Also skip during initial model construction
        if name != "updated_at" and hasattr(self, "updated_at"):
            super().__setattr__("updated_at", datetime.now())

    def write(self) -> None:
        """Save this deployment to the deployments file.

        This method loads the current deployments, updates this deployment's entry,
        and saves it back to ~/.vantage-cli/deployments.yaml.

        """
        from vantage_cli.sdk.cloud.schema import CloudType

        deployments_data = load_deployments()
        # Use mode='python' to serialize properly
        deployment_dict = self.model_dump(mode="python")

        # Ensure CloudType enums are serialized as strings
        if "credential" in deployment_dict and deployment_dict["credential"]:
            cred = deployment_dict["credential"]
            if isinstance(cred.get("credential_type"), CloudType):
                cred["credential_type"] = cred["credential_type"].value

        deployments_data["deployments"][str(self.id)] = deployment_dict
        save_deployments(deployments_data)

    @computed_field
    @property
    def name(self) -> str:
        """Get the deployment name based on app, cluster, and creation time."""
        return f"{self.app_name}-{self.cluster.name}-{self.created_at_as_timestamp_str[:5]}"

    @computed_field
    @property
    def cluster_name(self) -> str:
        """Get the cluster name from the cluster object."""
        return self.cluster.name

    @computed_field
    @property
    def cluster_id(self) -> str:
        """Get the cluster ID (client_id) from the cluster object."""
        return self.cluster.client_id

    @computed_field
    @property
    def is_active(self) -> bool:
        """Check if the deployment is active."""
        return self.status.lower() == "active"

    @computed_field
    @property
    def formatted_created_at(self) -> str:
        """Get formatted creation timestamp."""
        try:
            return self.created_at.strftime("%Y-%m-%d %H:%M")
        except (ValueError, AttributeError):
            return str(self.created_at)

    @computed_field
    @property
    def created_at_as_timestamp_str(self) -> str:
        """Get creation timestamp as a string with only numbers (no dots, dashes, or colons).

        Format: YYYYMMDDHHMMSSffffff (e.g., 20251010123045123456)
        """
        try:
            return self.created_at.strftime("%Y%m%d%H%M%S%f")
        except (ValueError, AttributeError):
            # Fallback: use timestamp as integer string
            return str(int(self.created_at.timestamp() * 1000000))

    @computed_field
    @property
    def compatible_integrations(self) -> list[str]:
        """Get a list of compatible integration types based on the cloud type."""
        return self.cloud.substrates
