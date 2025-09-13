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
"""Network management commands for Vantage CLI."""

from vantage_cli import AsyncTyper

from .attach import attach_network
from .create import create_network
from .delete import delete_network
from .detach import detach_network
from .get import get_network
from .list import list_networks
from .update import update_network

# Create the network command group
network_app = AsyncTyper(
    name="network",
    help="Manage virtual networks, subnets, and network configurations for cloud infrastructure.",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Register all commands
network_app.command("attach")(attach_network)
network_app.command("create")(create_network)
network_app.command("delete")(delete_network)
network_app.command("detach")(detach_network)
network_app.command("get")(get_network)
network_app.command("list")(list_networks)
network_app.command("update")(update_network)
