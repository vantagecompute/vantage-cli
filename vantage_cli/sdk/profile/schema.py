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
"""Profile schemas for the Vantage CLI."""

from pydantic import BaseModel, computed_field

from vantage_cli.config import Settings


class Profile(BaseModel):
    """Schema for profile data."""

    name: str
    settings: Settings
    is_active: bool = False

    @computed_field
    @property
    def api_base_url(self) -> str:
        """Get the API base URL from settings."""
        return self.settings.get_apis_url()

    @computed_field
    @property
    def tunnel_url(self) -> str:
        """Get the Tunnel URL from settings."""
        return self.settings.get_tunnel_url()

    @computed_field
    @property
    def ldap_url(self) -> str:
        """Get the ldap URL from settings."""
        return self.settings.get_ldap_url()

    @computed_field
    @property
    def oidc_base_url(self) -> str:
        """Get the OIDC base URL from settings."""
        return self.settings.get_auth_url()

    @computed_field
    @property
    def oidc_client_id(self) -> str:
        """Get the OIDC client ID from settings."""
        return self.settings.oidc_client_id
