# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Clouds management commands package."""

from vantage_cli import AsyncTyper

from .add import add_command
from .delete import delete_command
from .get import get_command
from .list import list_command
from .update import update_command

clouds_app = AsyncTyper(
    name="cloud",
    help="Manage cloud provider configurations and integrations for your Vantage infrastructure.",
    no_args_is_help=True,
)

# Register all commands
clouds_app.command("add")(add_command)
clouds_app.command("delete")(delete_command)
clouds_app.command("get")(get_command)
clouds_app.command("list")(list_command)
clouds_app.command("update")(update_command)
