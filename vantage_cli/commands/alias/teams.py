# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Alias command for teams -> team list."""

import typer

from vantage_cli.commands.team.list import list_teams


async def teams_command(
    ctx: typer.Context,
):
    """List all teams (alias for 'vantage team list')."""
    # The team list command reads JSON setting from context
    await list_teams(ctx)
