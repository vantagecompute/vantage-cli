# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Federation management commands for Vantage CLI."""

from vantage_cli import AsyncTyper

from .create import create_federation
from .delete import delete_federation
from .get import get_federation
from .list import list_federations
from .update import update_federation

# Create the federation command group
federation_app = AsyncTyper(
    name="federation",
    help="Manage Vantage compute federations for distributed workloads.",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Register subcommands directly
federation_app.command("create")(create_federation)
federation_app.command("delete")(delete_federation)
federation_app.command("get")(get_federation)
federation_app.command("list")(list_federations)
federation_app.command("update")(update_federation)
