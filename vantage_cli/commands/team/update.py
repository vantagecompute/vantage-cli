# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Update team command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def update_team(
    ctx: typer.Context, team_id: Annotated[str, typer.Argument(help="ID of the team to update")]
):
    """Update team settings."""
    if get_effective_json_output(ctx):
        print_json(data={"team_id": team_id, "status": "updated"})
    else:
        console.print(f"🔄 Team {team_id} updated successfully!")
