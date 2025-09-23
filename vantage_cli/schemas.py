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
"""Data models and schemas for the Vantage CLI."""

from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, computed_field
from rich.console import Console

from vantage_cli.config import Settings
from vantage_cli.constants import PROVIDER_SUBSTRATE_MAPPINGS


class TokenSet(BaseModel):
    """OAuth token set containing access and refresh tokens."""

    access_token: str
    refresh_token: Optional[str] = None


class IdentityData(BaseModel):
    """User identity information extracted from tokens."""

    client_id: str
    email: Optional[str] = None


class Persona(BaseModel):
    """User persona combining token set and identity data."""

    token_set: TokenSet
    identity_data: IdentityData


class DeviceCodeData(BaseModel):
    """OAuth device code flow data."""

    device_code: str
    verification_uri_complete: str
    interval: int


class CliContext(BaseModel, arbitrary_types_allowed=True):
    """CLI context for command execution."""

    profile: str = "default"
    verbose: bool = False
    json_output: bool = False
    persona: Optional[Persona] = None
    client: Optional[httpx.AsyncClient] = None
    settings: Optional[Settings] = None
    console: Optional[Console] = None
    command_start_time: Optional[float] = None


class VantageClusterContext(BaseModel):
    """Vantage cluster context."""

    cluster_name: str
    client_id: str
    client_secret: str
    oidc_domain: str
    oidc_base_url: str
    base_api_url: str
    tunnel_api_url: str
    jupyterhub_token: str


class ClusterDetailSchema(VantageClusterContext):
    """VantageClusterContext + status, description, owner_email, provider, cloud_account_id, creation_parameters."""

    status: str
    description: str
    owner_email: str
    provider: str
    cloud_account_id: Optional[str] = None
    creation_parameters: Dict[str, Any]


class Deployment(BaseModel):
    """Schema for deployment data."""

    # Core identification
    name: str
    app_name: str
    # Cloud and infrastructure details
    cloud: str
    deployment_type: Optional[str] = None
    k8s_namespaces: Optional[List[str]] = None

    # Status and timestamps
    status: str
    created_at: str
    updated_at: Optional[str] = None

    # Extended data
    cluster_data: Optional[VantageClusterContext] = None
    metadata: Dict[str, Any] = {}

    @computed_field
    @property
    def compatible_integrations(self) -> list[str]:
        """Get a list of compatible integration types based on the cloud type."""
        return PROVIDER_SUBSTRATE_MAPPINGS.get(self.cloud, [])
