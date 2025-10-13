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
"""Cloud Credential CRUD SDK for managing cloud credentials."""

import logging
from typing import Dict, List, Optional

from vantage_cli.sdk.cloud.schema import CloudType
from vantage_cli.sdk.cloud_credential.schema import CloudCredential

logger = logging.getLogger(__name__)


class CloudCredentialSDK:
    """SDK for managing cloud credentials.

    This SDK provides CRUD operations for cloud provider credentials,
    storing API keys, service account credentials, and other authentication data.
    Credentials are persisted to ~/.vantage-cli/credentials.yaml.
    """

    def __init__(self):
        """Initialize the Cloud Credential SDK."""
        self._credentials: Dict[str, CloudCredential] = {}
        self._load_from_file()
        logger.debug("Initialized CloudCredentialSDK")

    def _load_from_file(self):
        """Load credentials from the YAML file."""
        from vantage_cli.sdk.cloud_credential.schema import load_credentials

        credentials_data = load_credentials()
        for cred_id, cred_dict in credentials_data.get("credentials", {}).items():
            try:
                credential = CloudCredential(**cred_dict)
                self._credentials[credential.id] = credential
            except Exception as e:
                logger.warning(f"Failed to load credential {cred_id}: {e}")

        logger.debug(f"Loaded {len(self._credentials)} credentials from file")

    def create(
        self,
        name: str,
        credential_type: CloudType,
        cloud_id: str,
        credentials_data: Dict,
    ) -> CloudCredential:
        """Create a new cloud credential.

        Args:
            name: Human-readable credential name
            credential_type: Type of cloud provider
            cloud_id: ID of the associated cloud
            credentials_data: Dictionary containing credential data

        Returns:
            Created CloudCredential instance
        """
        credential = CloudCredential(
            name=name,
            credential_type=credential_type,
            cloud_id=cloud_id,
            credentials_data=credentials_data,
        )

        self._credentials[credential.id] = credential
        credential.write()  # Persist to file
        logger.debug(f"Created credential '{name}' (ID: {credential.id}) for cloud {cloud_id}")

        return credential

    def get(self, credential_id: str) -> Optional[CloudCredential]:
        """Get a credential by ID.

        Args:
            credential_id: ID of the credential

        Returns:
            CloudCredential instance or None
        """
        return self._credentials.get(credential_id)

    def get_default(self, cloud_name: str) -> Optional[CloudCredential]:
        """Get the default credential for a specific cloud.

        Args:
            cloud_name: Name of the cloud (e.g., 'aws', 'gcp', 'cudo-compute')

        Returns:
            Default CloudCredential instance for the cloud or None if not found
        """
        from vantage_cli.sdk.cloud import cloud_sdk

        # Get the cloud by name to find its ID
        cloud = cloud_sdk.get(cloud_name)
        if not cloud:
            logger.warning(f"Cloud '{cloud_name}' not found")
            return None

        # Find the default credential for this cloud
        for credential in self._credentials.values():
            if credential.cloud_id == cloud.id and credential.default:
                logger.debug(
                    f"Found default credential '{credential.name}' for cloud '{cloud_name}'"
                )
                return credential

        logger.debug(f"No default credential found for cloud '{cloud_name}'")
        return None

    def list(
        self,
        cloud_id: Optional[str] = None,
        credential_type: Optional[CloudType] = None,
    ) -> List[CloudCredential]:
        """List credentials with optional filtering.

        Args:
            cloud_id: Filter by cloud ID
            credential_type: Filter by credential type

        Returns:
            List of CloudCredential instances
        """
        credentials = list(self._credentials.values())

        # Filter by cloud ID
        if cloud_id:
            credentials = [c for c in credentials if c.cloud_id == cloud_id]

        # Filter by credential type
        if credential_type:
            credentials = [c for c in credentials if c.credential_type == credential_type]

        return credentials

    def delete(self, credential_id: str) -> bool:
        """Delete a credential by ID.

        Args:
            credential_id: ID of the credential to delete

        Returns:
            True if deleted, False if not found
        """
        if credential_id in self._credentials:
            del self._credentials[credential_id]

            # Remove from file
            from vantage_cli.sdk.cloud_credential.schema import load_credentials, save_credentials

            credentials_data = load_credentials()
            if credential_id in credentials_data.get("credentials", {}):
                del credentials_data["credentials"][credential_id]
                save_credentials(credentials_data)

            logger.debug(f"Deleted credential {credential_id}")
            return True
        return False

    def update(
        self,
        credential_id: str,
        name: Optional[str] = None,
        credentials_data: Optional[Dict] = None,
        set_as_default: bool = False,
    ) -> Optional[CloudCredential]:
        """Update a credential.

        Args:
            credential_id: ID of the credential to update
            name: New name (optional)
            credentials_data: New credentials data (optional)
            set_as_default: Set this credential as default for its cloud type

        Returns:
            Updated CloudCredential instance or None if not found
        """
        credential = self._credentials.get(credential_id)
        if not credential:
            return None

        if name is not None:
            credential.name = name

        if credentials_data is not None:
            credential.credentials_data = credentials_data

        if set_as_default:
            # First, unset default for all other credentials of the same cloud type
            for cred in self._credentials.values():
                if cred.credential_type == credential.credential_type and cred.id != credential_id:
                    cred.default = False
                    cred.write()

            # Set this credential as default
            credential.default = True

        credential.write()  # Persist changes to file
        logger.debug(f"Updated credential {credential_id}")
        return credential


# Create singleton instance
cloud_credential_sdk = CloudCredentialSDK()


__all__ = [
    "CloudCredentialSDK",
    "cloud_credential_sdk",
]
