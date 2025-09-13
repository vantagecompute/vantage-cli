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
"""License deployment management commands."""

from vantage_cli import AsyncTyper

from .create import create_license_deployment
from .delete import delete_license_deployment
from .get import get_license_deployment
from .list import list_license_deployments
from .update import update_license_deployment

# Create the license deployment command group
deployment_app = AsyncTyper(
    name="deployment",
    help="Manage license deployments for software distribution and activation.",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Register all commands
deployment_app.command("create")(create_license_deployment)
deployment_app.command("delete")(delete_license_deployment)
deployment_app.command("get")(get_license_deployment)
deployment_app.command("list")(list_license_deployments)
deployment_app.command("update")(update_license_deployment)
