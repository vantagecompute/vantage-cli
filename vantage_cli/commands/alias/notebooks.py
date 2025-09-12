# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Alias command for notebooks -> notebook list."""

import typer

from vantage_cli.commands.notebook.list import list_notebooks


async def notebooks_command(
    ctx: typer.Context,
):
    """List all notebooks (alias for 'vantage notebook list')."""
    # The notebook list command doesn't support JSON output yet (stub)
    await list_notebooks(ctx)
