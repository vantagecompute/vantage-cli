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
"""Cloud Credential schema definitions."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

import yaml
from pydantic import BaseModel, Field

from vantage_cli.constants import VANTAGE_CLI_CREDENTIALS_FILE as CREDENTIALS_YAML
from vantage_cli.sdk.cloud.schema import CloudType


def load_credentials() -> Dict[str, Any]:
    """Load credentials data from ~/.vantage-cli/credentials.yaml.

    Returns:
        Dictionary containing credentials data with 'credentials' key
    """
    if not CREDENTIALS_YAML.exists():
        return {"credentials": {}}

    try:
        data = yaml.safe_load(CREDENTIALS_YAML.read_text())
        if "credentials" not in data:
            data["credentials"] = {}
        return data
    except Exception:
        # Return empty dict with defaults on error
        return {"credentials": {}}


def save_credentials(credentials_data: Dict[str, Any]) -> None:
    """Save credentials data to ~/.vantage-cli/credentials.yaml.

    Args:
        credentials_data: Dictionary containing credentials data
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Ensure the directory exists
        CREDENTIALS_YAML.parent.mkdir(parents=True, exist_ok=True)
        CREDENTIALS_YAML.write_text(
            yaml.dump(credentials_data, default_flow_style=False, indent=2)
        )
    except Exception as e:
        logger.error(f"Failed to save credentials to {CREDENTIALS_YAML}: {e}")


class CloudCredential(BaseModel):
    """Cloud credential model for storing cloud provider credentials."""

    model_config = {
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "id": "cred-123",
                "name": "AWS Production",
                "credential_type": "aws",
                "cloud_id": "cloud-456",
                "credentials_data": {
                    "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                    "secret_access_key": "***",
                    "region": "us-west-2",
                },
            }
        },
    }

    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique credential ID")
    name: str = Field(..., description="Human-readable credential name")
    credential_type: CloudType = Field(
        ..., description="Type of cloud provider (aws, gcp, azure, etc.)"
    )
    cloud_id: str = Field(..., description="ID of the associated cloud")
    credentials_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Encrypted credential data (API keys, service accounts, etc.)",
    )
    default: bool = Field(
        default=False, description="Whether this is the default credential for this cloud type"
    )
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.now, description="Last update timestamp"
    )

    def __setattr__(self, name: str, value: Any) -> None:
        """Override setattr to auto-update updated_at when any field changes.

        This ensures that whenever a field is modified (e.g., credential.name = "New Name"),
        the updated_at timestamp is automatically refreshed.
        """
        # Call parent setattr first
        super().__setattr__(name, value)

        # Auto-update updated_at for any field change except updated_at itself
        # Also skip during initial model construction
        if name != "updated_at" and hasattr(self, "updated_at"):
            super().__setattr__("updated_at", datetime.now())

    def write(self) -> None:
        """Save this credential to the credentials file.

        This method loads the current credentials, updates this credential's entry,
        and saves it back to ~/.vantage-cli/credentials.yaml.
        """
        credentials_data = load_credentials()
        # Use mode='python' to serialize enums as their values
        cred_dict = self.model_dump(mode="python")
        # Ensure credential_type is serialized as a string value
        if isinstance(cred_dict.get("credential_type"), CloudType):
            cred_dict["credential_type"] = cred_dict["credential_type"].value
        credentials_data["credentials"][str(self.id)] = cred_dict
        save_credentials(credentials_data)


__all__ = [
    "CloudCredential",
]
