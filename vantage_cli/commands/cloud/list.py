# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""List command for cloud provider configurations."""

import typer
from rich.console import Console

# NO IMPORTS NEEDED! The --json option is auto-injected by AsyncTyper
from .render import render_clouds_table

console = Console()


def list_command(
    ctx: typer.Context,
) -> None:
    """List all configured cloud providers.

    Displays a list of all cloud provider configurations including their status,
    regions, and basic connection information.

    Args:
        ctx: The Typer context
    """
    # Get JSON flag from context (automatically set by AsyncTyper)
    use_json = getattr(ctx.obj, "json_output", False) if ctx.obj else False

    # Mock cloud data - in a real implementation, this would fetch from the backend
    mock_clouds = [
        {
            "name": "aws-production",
            "provider": "aws",
            "region": "us-west-2",
            "status": "active",
            "created_at": "2025-09-10T05:00:00Z",
        },
        {
            "name": "gcp-staging",
            "provider": "gcp",
            "region": "us-central1",
            "status": "active",
            "created_at": "2025-09-08T12:30:00Z",
        },
        {
            "name": "azure-dev",
            "provider": "azure",
            "region": "eastus",
            "status": "inactive",
            "created_at": "2025-09-05T09:15:00Z",
        },
    ]

    if use_json:
        from rich import print_json

        print_json(data={"clouds": mock_clouds})
    else:
        render_clouds_table(mock_clouds)
