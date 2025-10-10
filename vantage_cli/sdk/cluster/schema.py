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
"""Cluster schemas for the Vantage CLI."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, computed_field


class VantageClusterContext(BaseModel):
    """Vantage cluster context."""

    cluster_name: str
    client_id: str
    client_secret: str
    oidc_domain: str
    oidc_base_url: str
    base_api_url: str
    tunnel_api_url: str
    ldap_url: str
    sssd_binder_password: str
    org_id: str
    jupyterhub_token: str


class ClusterDetailSchema(VantageClusterContext):
    """VantageClusterContext + status, description, owner_email, provider, cloud_account_id, creation_parameters."""

    status: str
    description: str
    owner_email: str
    provider: str
    cloud_account_id: Optional[str] = None
    creation_parameters: Dict[str, Any]


class Cluster(BaseModel):
    """Schema for cluster data."""

    name: str
    status: str
    client_id: str
    client_secret: Optional[str] = None
    description: str
    owner_email: str
    provider: str
    cloud_account_id: Optional[str] = None
    creation_parameters: Dict[str, Any] = {}
    sssd_binder_password: Optional[str] = None

    @computed_field
    @property
    def jupyterhub_url(self) -> str:
        """Return the computed jupyterhub url."""
        return f"https://{self.client_id}.vantagecompute.ai"

    @computed_field
    @property
    def jupyterhub_token(self) -> str:
        """Return the computed JupyterHub token."""
        return self.creation_parameters.get("jupyterhub_token", "")

    @computed_field
    @property
    def is_ready(self) -> bool:
        """Check if the cluster is ready."""
        return self.status.lower() == "ready"

    @computed_field
    @property
    def cluster_type(self) -> str:
        """Get cluster type based on provider."""
        provider_mapping = {
            "on_prem": "On-Premises",
            "aws": "AWS",
            "gcp": "Google Cloud",
            "azure": "Azure",
            "localhost": "Local",
        }
        return provider_mapping.get(self.provider, self.provider.title())
