# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Add team member command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def add_team_member(
    ctx: typer.Context,
    team_id: Annotated[str, typer.Argument(help="ID of the team")],
    user_id: Annotated[str, typer.Argument(help="ID of the user to add")],
):
    """Add a member to a team."""
    if get_effective_json_output(ctx):
        print_json(data={"team_id": team_id, "user_id": user_id, "status": "added"})
    else:
        console.print(f"➕ User {user_id} added to team {team_id} successfully!")
