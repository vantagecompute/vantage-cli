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
"""License schemas for the Vantage CLI SDK."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LicenseServer(BaseModel):
    """Schema for license server."""

    id: str = Field(..., description="License server ID")
    name: str = Field(..., description="Server name")
    host: str = Field(..., description="Server host address")
    port: int = Field(..., description="Server port")
    license_type: str = Field(..., description="License type (e.g., FlexLM, RLM)")
    status: str = Field(..., description="Server status")
    owner_email: str = Field(..., description="Owner email address")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    description: Optional[str] = Field(None, description="Server description")


class LicenseFeature(BaseModel):
    """Schema for license feature."""

    id: str = Field(..., description="Feature ID")
    name: str = Field(..., description="Feature name")
    server_id: str = Field(..., description="Associated license server ID")
    product_id: Optional[str] = Field(None, description="Associated product ID")
    total_licenses: int = Field(..., description="Total number of licenses")
    in_use: int = Field(0, description="Number of licenses currently in use")
    available: int = Field(..., description="Number of available licenses")
    owner_email: str = Field(..., description="Owner email address")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    description: Optional[str] = Field(None, description="Feature description")
    version: Optional[str] = Field(None, description="Feature version")
    expiration_date: Optional[datetime] = Field(None, description="License expiration date")


class LicenseProduct(BaseModel):
    """Schema for license product."""

    id: str = Field(..., description="Product ID")
    name: str = Field(..., description="Product name")
    vendor: str = Field(..., description="Product vendor")
    owner_email: str = Field(..., description="Owner email address")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    description: Optional[str] = Field(None, description="Product description")
    version: Optional[str] = Field(None, description="Product version")
    features: List[str] = Field(default_factory=list, description="Associated feature IDs")


class LicenseConfiguration(BaseModel):
    """Schema for license configuration."""

    id: str = Field(..., description="Configuration ID")
    name: str = Field(..., description="Configuration name")
    server_id: str = Field(..., description="Associated license server ID")
    configuration_type: str = Field(..., description="Configuration type")
    configuration_data: Dict[str, Any] = Field(
        default_factory=dict, description="Configuration data"
    )
    owner_email: str = Field(..., description="Owner email address")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    description: Optional[str] = Field(None, description="Configuration description")
    is_active: bool = Field(True, description="Whether configuration is active")


class LicenseBooking(BaseModel):
    """Schema for license booking/reservation."""

    id: str = Field(..., description="Booking ID")
    feature_id: str = Field(..., description="Associated feature ID")
    user_email: str = Field(..., description="User email who made the booking")
    cluster_id: Optional[str] = Field(None, description="Associated cluster ID")
    num_licenses: int = Field(..., description="Number of licenses booked")
    start_time: datetime = Field(..., description="Booking start time")
    end_time: Optional[datetime] = Field(None, description="Booking end time")
    status: str = Field(..., description="Booking status (active, expired, cancelled)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    description: Optional[str] = Field(None, description="Booking description")


class LicenseDeployment(BaseModel):
    """Schema for license deployment."""

    id: str = Field(..., description="Deployment ID")
    server_id: str = Field(..., description="Associated license server ID")
    cluster_id: str = Field(..., description="Associated cluster ID")
    deployment_status: str = Field(..., description="Deployment status")
    owner_email: str = Field(..., description="Owner email address")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    description: Optional[str] = Field(None, description="Deployment description")
    configuration_id: Optional[str] = Field(None, description="Associated configuration ID")
    endpoint_url: Optional[str] = Field(None, description="Deployment endpoint URL")
