# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Profile management commands for Vantage CLI."""

import typer
from rich.console import Console

from .crud import create_profile, delete_profile, get_profile, list_profiles, use_profile

console = Console()

# Create the profile app
profile_app = typer.Typer(
    name="profile",
    help="Manage Vantage CLI profiles to work with different environments and configurations.",
    invoke_without_command=True,
    no_args_is_help=True,
    context_settings={
        "allow_extra_args": True,
        "allow_interspersed_args": True,
        "ignore_unknown_options": True,
    },
)

# Register subcommands
profile_app.command("create")(create_profile)
profile_app.command("delete")(delete_profile)
profile_app.command("get")(get_profile)
profile_app.command("list")(list_profiles)
profile_app.command("use")(use_profile)
