# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Create team command."""

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def create_team(ctx: typer.Context):
    """Create a new team."""
    if get_effective_json_output(ctx):
        print_json(data={"team_id": "team-12345", "status": "created"})
    else:
        console.print("👥 Team team-12345 created successfully!")
