# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Alias command for profiles -> profile list."""

import typer

from vantage_cli.commands.profile.crud import list_profiles


def profiles_command(
    ctx: typer.Context,
):
    """List all profiles (alias for 'vantage profile list')."""
    # Extract flags from the AsyncTyper context
    json_output = getattr(ctx.obj, "json_output", False) if ctx.obj else False
    verbose = getattr(ctx.obj, "verbose", False) if ctx.obj else False
    list_profiles(ctx, json_output=json_output, verbose=verbose)
