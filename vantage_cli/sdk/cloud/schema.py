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
"""Cloud schemas."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, computed_field


class VantageProviderLabel(str, Enum):
    """Vantage provider labels for cloud providers."""

    ON_PREM = "on_prem"
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    CUDO = "on_prem"


class CloudType(str, Enum):
    """Cloud provider types."""

    LOCALHOST = "localhost"
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    CUDO_COMPUTE = "cudo-compute"
    ON_PREMISES = "on-premises"


class Cloud(BaseModel):
    """Cloud model."""

    id: str
    vantage_provider_label: VantageProviderLabel = Field(
        ..., description="Vantage provider label for GraphQL API"
    )
    substrates: List[str] = Field(
        default_factory=list,
        description="Available substrates for this cloud (e.g., 'k8s', 'metal', 'lxd')",
    )
    enabled: bool = Field(default=True, description="Whether this cloud is enabled")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional cloud metadata")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @computed_field
    @property
    def name(self) -> str:
        """Alias for id."""
        return self.id

    class Config:
        """Pydantic model configuration."""

        use_enum_values = True


class VantageClouds(BaseModel):
    """Collection of Vantage-supported clouds."""

    clouds: List[Cloud] = Field(default_factory=list, description="List of clouds")

    def get_by_name(self, name: str) -> Optional[Cloud]:
        """Get a cloud by name."""
        for cloud in self.clouds:
            if cloud.name == name:
                return cloud
        return None

    def get_by_id(self, cloud_id: str) -> Optional[Cloud]:
        """Get a cloud by ID."""
        for cloud in self.clouds:
            if cloud.id == cloud_id:
                return cloud
        return None

    def get_by_type(self, vantage_label: VantageProviderLabel) -> List[Cloud]:
        """Get all clouds with a specific Vantage provider label."""
        return [
            cloud
            for cloud in self.clouds
            if cloud.vantage_provider_label == vantage_label
            or cloud.vantage_provider_label == vantage_label.value
        ]

    def get_enabled(self) -> List[Cloud]:
        """Get all enabled clouds."""
        return [cloud for cloud in self.clouds if cloud.enabled]


__all__ = [
    "Cloud",
    "CloudType",
    "VantageProviderLabel",
    "VantageClouds",
]
