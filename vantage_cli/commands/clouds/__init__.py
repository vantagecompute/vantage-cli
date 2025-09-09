# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Clouds management commands package."""

import typer

from .add import add_command
from .delete import delete_command
from .update import update_command

clouds_app = typer.Typer(
    name="clouds",
    help="Manage cloud provider configurations and integrations for your Vantage infrastructure.",
    no_args_is_help=True,
)

# Register all commands
clouds_app.command("add")(add_command)
clouds_app.command("delete")(delete_command)
clouds_app.command("update")(update_command)
