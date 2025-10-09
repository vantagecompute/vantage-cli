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

from uuid import UUID, uuid4

from pydantic import BaseModel, computed_field, Field

from vantage_cli.constants import PROVIDER_SUBSTRATE_MAPPINGS
from vantage_cli.sdk.cluster.schema import VantageClusterContext

from vantage_cli.sdk.cluster.schema import Cluster


class Deployment(BaseModel):
    """Schema for deployment data.
    
    The updated_at field is automatically refreshed whenever any field
    in the model is modified (e.g., deployment.status = "active").
    This happens transparently without requiring any user action.
    """
    
    model_config = {"validate_assignment": True}

    id: UUID = Field(default_factory=uuid4)
    app_name: str
    cluster: Cluster
    vantage_cluster_ctx: VantageClusterContext
    cloud_provider: str
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
        if name != 'updated_at' and hasattr(self, 'updated_at'):
            super().__setattr__('updated_at', datetime.now())
    
    def write(self) -> None:
        """Save this deployment to the deployments file.
        
        This method loads the current deployments, updates this deployment's entry,
        and saves it back to ~/.vantage-cli/deployments.yaml.
        
        """
        # Import here to avoid circular dependencies
        from vantage_cli.apps.common import load_deployments, save_deployments
        
        # Load existing deployments
        deployments_data = load_deployments()
        
        # Update this deployment's entry (using str(self.id) since YAML keys are strings)
        deployments_data["deployments"][str(self.id)] = self.model_dump()
        
        # Save back to file
        save_deployments(deployments_data)

    @computed_field
    @property
    def name(self) -> str:
        return f"{self.app_name}-{self.cluster.name}-{self.created_at.timestamp()}"

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
    def compatible_integrations(self) -> list[str]:
        """Get a list of compatible integration types based on the cloud type."""
        return PROVIDER_SUBSTRATE_MAPPINGS.get(self.cloud_provider, [])
