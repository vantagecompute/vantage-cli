# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Configuration management commands for Vantage CLI."""

from rich.console import Console

from vantage_cli import AsyncTyper

from .clear import clear_config

console = Console()

# Create the config app
config_app = AsyncTyper(
    name="config",
    help="Manage Vantage CLI configuration and settings.",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Register subcommands
config_app.command("clear")(clear_config)
