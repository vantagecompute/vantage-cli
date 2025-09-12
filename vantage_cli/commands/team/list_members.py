# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""List team members command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def list_team_members(
    ctx: typer.Context, team_id: Annotated[str, typer.Argument(help="ID of the team")]
):
    """List all team members."""
    if get_effective_json_output(ctx):
        print_json(
            data={
                "team_id": team_id,
                "members": [
                    {"user_id": "user-123", "username": "alice", "role": "admin"},
                    {"user_id": "user-456", "username": "bob", "role": "member"},
                ],
            }
        )
    else:
        console.print(f"👥 Members of team {team_id}:")
        console.print("  alice (admin)")
        console.print("  bob (member)")
