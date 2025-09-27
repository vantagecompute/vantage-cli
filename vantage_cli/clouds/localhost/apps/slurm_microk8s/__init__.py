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
"""The vantage-cli application for deploying slurm to microk8s on localhost."""

from .app import (
    cleanup_microk8s_localhost,
    create,
    create_command,
    remove_command,
    status_command,
)

__all__ = [
    "cleanup_microk8s_localhost",
    "create",
    "create_command",
    "remove_command",
    "status_command",
]
