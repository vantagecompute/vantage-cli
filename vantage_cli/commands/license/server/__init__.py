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
"""License server management commands."""

from vantage_cli import AsyncTyper

from .create import create_license_server
from .delete import delete_license_server
from .get import get_license_server
from .list import list_license_servers
from .update import update_license_server

# Create the license server command group
server_app = AsyncTyper(
    name="server",
    help="Manage license servers for software licensing and compliance.",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Register all commands
server_app.command("create")(create_license_server)
server_app.command("delete")(delete_license_server)
server_app.command("get")(get_license_server)
server_app.command("list")(list_license_servers)
server_app.command("update")(update_license_server)
