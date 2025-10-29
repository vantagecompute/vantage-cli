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
"""Profile schema for the Vantage CLI."""

import json
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, computed_field

from vantage_cli.config import Settings
from vantage_cli.constants import USER_CONFIG_FILE
from vantage_cli.sdk.cloud_credential.schema import CloudCredential

logger = logging.getLogger(__name__)


def load_profiles() -> Dict[str, Any]:
    """Load profiles data from ~/.vantage-cli/profiles.json.

    Returns:
        Dictionary containing profile settings data
    """
    if not USER_CONFIG_FILE.exists():
        return {}

    try:
        data = json.loads(USER_CONFIG_FILE.read_text())
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_profiles(profiles_data: Dict[str, Any]) -> None:
    """Save profiles data to ~/.vantage-cli/profiles.json.

    Args:
        profiles_data: Dictionary containing profile settings data
    """
    try:
        # Ensure the directory exists
        USER_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        USER_CONFIG_FILE.write_text(json.dumps(profiles_data, indent=2))
    except Exception as e:
        logger.error(f"Failed to save profiles to {USER_CONFIG_FILE}: {e}")


class Profile(BaseModel):
    """Schema for profile data."""

    name: str
    settings: Settings
    is_active: bool = False
    cloud_credentials: Optional[List[CloudCredential]] = None

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

    def write(self) -> None:
        """Save this profile to the profiles file.

        This method saves the profile settings to ~/.vantage-cli/profiles.json.
        """
        from vantage_cli.config import dump_settings

        # Save settings using the existing config function
        dump_settings(self.name, self.settings)


__all__ = [
    "Profile",
    "load_profiles",
    "save_profiles",
]
