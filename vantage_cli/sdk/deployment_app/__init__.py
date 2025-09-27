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
"""Deployment App SDK for managing available deployment applications."""

from vantage_cli.sdk.deployment_app.crud import DeploymentAppSDK
from vantage_cli.sdk.deployment_app.schema import DeploymentApp

__all__ = ["DeploymentApp", "DeploymentAppSDK", "deployment_app_sdk"]

# Lazy-loaded singleton instance
_deployment_app_sdk_instance = None


def _get_deployment_app_sdk() -> DeploymentAppSDK:
    """Get or create the singleton DeploymentAppSDK instance.

    Uses lazy initialization to avoid running discovery during module import,
    which would log debug messages before logging is configured.
    """
    global _deployment_app_sdk_instance
    if _deployment_app_sdk_instance is None:
        _deployment_app_sdk_instance = DeploymentAppSDK()
    return _deployment_app_sdk_instance


# Property-like access for the singleton
class _DeploymentAppSDKProxy:
    """Proxy object that lazily initializes the SDK on first access."""

    def __getattr__(self, name):
        sdk = _get_deployment_app_sdk()
        return getattr(sdk, name)


# Create the proxy instance
deployment_app_sdk = _DeploymentAppSDKProxy()
