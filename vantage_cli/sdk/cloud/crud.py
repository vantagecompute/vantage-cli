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
"""Cloud CRUD SDK for managing clouds."""

import logging
from typing import Dict, List, Optional

from vantage_cli.sdk.cloud.schema import (
    Cloud,
    VantageClouds,
    VantageProviderLabel,
)

logger = logging.getLogger(__name__)


class CloudSDK:
    """SDK for managing clouds.

    This SDK manages cloud providers and their supported substrates.
    Each cloud has a Vantage provider label and a list of supported substrates.
    """

    # Cloud configuration with substrates
    CLOUD_CONFIGS = {
        "localhost": {
            "vantage_label": VantageProviderLabel.ON_PREM,
            "substrates": ["multipass", "lxd", "microk8s"],
        },
        "aws": {
            "vantage_label": VantageProviderLabel.AWS,
            "substrates": ["eks", "ec2"],
        },
        "gcp": {
            "vantage_label": VantageProviderLabel.GCP,
            "substrates": ["gke", "gce"],
        },
        "azure": {
            "vantage_label": VantageProviderLabel.AZURE,
            "substrates": ["aks", "vm"],
        },
        "on-premises": {
            "vantage_label": VantageProviderLabel.ON_PREM,
            "substrates": ["metal", "k8s"],
        },
        "cudo-compute": {
            "vantage_label": VantageProviderLabel.ON_PREM,
            "substrates": ["metal", "k8s"],
        },
    }

    def __init__(self):
        """Initialize the Cloud SDK."""
        self._clouds: Dict[str, Cloud] = {}
        self._discover_clouds()

    def _discover_clouds(self):
        """Discover and register available clouds from built-in configuration."""
        logger.debug("Discovering clouds")

        # Register clouds from built-in configuration
        for cloud_id, config in self.CLOUD_CONFIGS.items():
            # Create Cloud instance
            cloud = Cloud(
                id=cloud_id,
                vantage_provider_label=config["vantage_label"],
                substrates=config["substrates"],
            )

            self._clouds[cloud_id] = cloud
            logger.debug(
                f"Registered cloud '{cloud_id}' - "
                f"label: {config['vantage_label'].value}, substrates: {config['substrates']}"
            )

        logger.debug(f"Discovered {len(self._clouds)} clouds")

    def list(
        self,
        enabled_only: bool = True,
        vantage_label: Optional[VantageProviderLabel] = None,
    ) -> List[Cloud]:
        """List clouds with optional filtering.

        Args:
            enabled_only: Only return enabled clouds
            vantage_label: Filter by Vantage provider label

        Returns:
            List of Cloud instances
        """
        clouds = list(self._clouds.values())

        # Filter by enabled status
        if enabled_only:
            clouds = [c for c in clouds if c.enabled]

        # Filter by Vantage label
        if vantage_label:
            clouds = [c for c in clouds if c.vantage_provider_label == vantage_label]
            logger.debug(f"Filtered clouds by label '{vantage_label}': {[c.name for c in clouds]}")

        return clouds

    def get(self, cloud_name: str) -> Optional[Cloud]:
        """Get a cloud by name.

        Args:
            cloud_name: Name of the cloud

        Returns:
            Cloud instance or None
        """
        return self._clouds.get(cloud_name)

    def get_by_id(self, cloud_id: str) -> Optional[Cloud]:
        """Get a cloud by ID.

        Args:
            cloud_id: ID of the cloud

        Returns:
            Cloud instance or None
        """
        for cloud in self._clouds.values():
            if cloud.id == cloud_id:
                return cloud
        return None

    def get_substrates(self, cloud_name: str) -> List[str]:
        """Get available substrates for a cloud.

        Args:
            cloud_name: Name of the cloud

        Returns:
            List of substrate names
        """
        cloud = self.get(cloud_name)
        return cloud.substrates if cloud else []

    def get_all_clouds(self) -> VantageClouds:
        """Get all clouds as a VantageClouds collection.

        Returns:
            VantageClouds instance containing all clouds
        """
        return VantageClouds(clouds=list(self._clouds.values()))

    def refresh(self):
        """Refresh the cloud registry by re-discovering clouds."""
        logger.debug("Refreshing cloud registry")
        self._clouds.clear()
        self._discover_clouds()


# Create singleton instance
cloud_sdk = CloudSDK()


__all__ = [
    "CloudSDK",
    "cloud_sdk",
]
