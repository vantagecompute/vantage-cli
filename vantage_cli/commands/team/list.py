# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""List teams command."""

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def list_teams(ctx: typer.Context):
    """List all teams."""
    if get_effective_json_output(ctx):
        print_json(
            data={
                "teams": [
                    {"team_id": "team-12345", "name": "Development Team", "member_count": 5},
                    {"team_id": "team-67890", "name": "QA Team", "member_count": 3},
                ]
            }
        )
    else:
        console.print("👥 Teams:")
        console.print("  team-12345 - Development Team (5 members)")
        console.print("  team-67890 - QA Team (3 members)")
