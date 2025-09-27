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
"""Deployment App schema for the Vantage CLI."""

from typing import Any, Optional

from pydantic import BaseModel

__all__ = ["DeploymentApp"]


class DeploymentApp(BaseModel, arbitrary_types_allowed=True):
    """Schema for a deployment application."""

    name: str
    """The app command name (e.g., 'slurm-lxd', 'slurm-metal')"""

    cloud: str
    """The cloud provider name (e.g., 'localhost', 'cudo-compute', 'aws')"""

    substrate: str
    """The substrate/platform type (e.g., 'lxd', 'metal', 'k8s', 'multipass', 'microk8s')"""

    module: Optional[Any] = None
    """The Python module containing the app implementation (if loaded)"""
