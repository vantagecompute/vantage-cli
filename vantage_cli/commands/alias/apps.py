# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Alias command for apps -> app list."""

import typer

from vantage_cli.commands.app.list import list_apps


async def apps_command(
    ctx: typer.Context,
):
    """List all applications (alias for 'vantage app list')."""
    await list_apps(ctx)
