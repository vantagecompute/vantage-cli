# Copyright (C) 2025 Vantage Compute Corporation
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
"""List command for cloud provider configurations."""

import typer

from vantage_cli.exceptions import handle_abort

# NO IMPORTS NEEDED! The --json option is auto-injected by AsyncTyper
from .render import render_clouds_table


@handle_abort
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
        # Handle case where ctx.obj might be None in tests
        console = getattr(ctx.obj, "console", None) if ctx.obj else None
        if console is None:
            # Fallback to standard console if no console available
            from rich.console import Console

            console = Console()
        render_clouds_table(mock_clouds, console)
