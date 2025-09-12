# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Alias command for clusters -> cluster list."""

import typer

from vantage_cli.commands.cluster.list import list_clusters


async def clusters_command(
    ctx: typer.Context,
):
    """List all clusters (alias for 'vantage cluster list')."""
    await list_clusters(ctx)
