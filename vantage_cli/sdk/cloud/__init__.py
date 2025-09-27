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
"""Cloud SDK for managing clouds."""

from vantage_cli.sdk.cloud.crud import (
    CloudSDK,
    cloud_sdk,
)
from vantage_cli.sdk.cloud.schema import (
    Cloud,
    CloudType,
    VantageClouds,
    VantageProviderLabel,
)

__all__ = [
    # SDK classes
    "CloudSDK",
    # SDK instances
    "cloud_sdk",
    # Schema classes
    "Cloud",
    "CloudType",
    "VantageProviderLabel",
    "VantageClouds",
]
