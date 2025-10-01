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

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, computed_field

from vantage_cli.constants import PROVIDER_SUBSTRATE_MAPPINGS
from vantage_cli.sdk.cluster.schema import VantageClusterContext


class Deployment(BaseModel):
    """Schema for deployment data."""

    deployment_id: str
    deployment_name: str
    app_name: str
    cluster_name: str
    cluster_id: str
    cloud: str
    created_at: str
    status: str
    updated_at: Optional[str] = None

    # Additional fields that might be present
    deployment_type: Optional[str] = None
    k8s_namespaces: Optional[List[str]] = None
    cluster_data: Optional[VantageClusterContext] = None
    metadata: Dict[str, Any] = {}

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
            from datetime import datetime

            dt = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, AttributeError):
            return self.created_at

    @computed_field
    @property
    def compatible_integrations(self) -> list[str]:
        """Get a list of compatible integration types based on the cloud type."""
        return PROVIDER_SUBSTRATE_MAPPINGS.get(self.cloud, [])
