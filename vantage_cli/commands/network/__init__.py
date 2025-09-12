# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
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
