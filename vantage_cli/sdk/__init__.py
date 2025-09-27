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
"""Vantage CLI SDK - Centralized CRUD operations for all resources."""

# Import base classes
from .base import BaseCRUDSDK, BaseGraphQLResourceSDK, BaseLocalResourceSDK

# Import SDK instances
from .cluster.crud import cluster_sdk
from .deployment.crud import deployment_sdk
from .profile.crud import profile_sdk

__all__ = [
    "BaseCRUDSDK",
    "BaseLocalResourceSDK",
    "BaseGraphQLResourceSDK",
    "cluster_sdk",
    "profile_sdk",
    "deployment_sdk",
]
