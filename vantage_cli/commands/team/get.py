# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Get team command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def get_team(
    ctx: typer.Context, team_id: Annotated[str, typer.Argument(help="ID of the team to retrieve")]
):
    """Get details of a specific team."""
    if get_effective_json_output(ctx):
        print_json(data={"team_id": team_id, "name": "Development Team", "member_count": 5})
    else:
        console.print(f"👥 Team details for {team_id}")
        console.print("  Name: Development Team")
        console.print("  Members: 5")
