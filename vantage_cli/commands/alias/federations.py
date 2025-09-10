# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Alias command for federations -> federation list."""

import typer

from vantage_cli.commands.federation.list import list_federations


async def federations_command(
    ctx: typer.Context,
):
    """List all federations (alias for 'vantage federation list')."""
    await list_federations(ctx)
