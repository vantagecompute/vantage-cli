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
"""Cloud Credential SDK for managing cloud provider credentials."""

from vantage_cli.sdk.cloud_credential.crud import (
    CloudCredentialSDK,
    cloud_credential_sdk,
)
from vantage_cli.sdk.cloud_credential.schema import (
    CloudCredential,
)

__all__ = [
    # SDK classes
    "CloudCredentialSDK",
    # SDK instances
    "cloud_credential_sdk",
    # Schema classes
    "CloudCredential",
]
