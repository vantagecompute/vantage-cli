# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Alias command for networks -> network list."""

import typer

from vantage_cli.commands.network.list import list_networks


async def networks_command(
    ctx: typer.Context,
):
    """List all networks (alias for 'vantage network list')."""
    await list_networks(ctx)
