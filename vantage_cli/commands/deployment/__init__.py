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
"""Deployment management commands for Vantage CLI."""

from vantage_cli import AsyncTyper

from .create import create_deployment
from .delete import delete_deployment
from .list import list_deployments

# Create the deployment command group
deployment_app = AsyncTyper(
    name="deployment",
    help="Create and manage application deployments on Vantage compute clusters.",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Register main deployment commands
deployment_app.command("list")(list_deployments)
deployment_app.command("create")(create_deployment)
deployment_app.command("delete")(delete_deployment)

__all__ = ["deployment_app"]
