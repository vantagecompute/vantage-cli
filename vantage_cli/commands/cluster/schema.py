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
