"""Schema definitions for cluster commands."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class VantageClusterContext(BaseModel):
    """Vantage cluster context for generating juju configuration."""

    client_id: str
    client_secret: str
    oidc_domain: str
    oidc_base_url: str
    base_api_url: str
    tunnel_api_url: str
    jupyterhub_token: str


class ClusterDetailSchema(BaseModel):
    """Schema for detailed cluster information."""

    name: str
    status: str
    client_id: str
    client_secret: Optional[str] = None
    description: str
    owner_mail: str
    provider: str
    cloud_account_id: Optional[str] = None
    creation_parameters: Dict[str, Any]
