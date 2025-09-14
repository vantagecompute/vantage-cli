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
"""Alias commands for vantage CLI."""

from .apps import apps_command
from .clouds import clouds_command
from .clusters import clusters_command
from .deployments import deployments_command
from .federations import federations_command
from .networks import networks_command
from .notebooks import notebooks_command
from .profiles import profiles_command
from .teams import teams_command

__all__ = [
    "apps_command",
    "deployments_command",
    "clouds_command",
    "clusters_command",
    "federations_command",
    "networks_command",
    "notebooks_command",
    "profiles_command",
    "teams_command",
]
