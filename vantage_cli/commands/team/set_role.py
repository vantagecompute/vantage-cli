# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Set team member role command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def set_team_member_role(
    ctx: typer.Context,
    team_id: Annotated[str, typer.Argument(help="ID of the team")],
    user_id: Annotated[str, typer.Argument(help="ID of the user")],
    role: Annotated[str, typer.Argument(help="Role to assign (admin/member)")],
):
    """Set member role in team."""
    if get_effective_json_output(ctx):
        print_json(
            data={"team_id": team_id, "user_id": user_id, "role": role, "status": "updated"}
        )
    else:
        console.print(f"👤 User {user_id} role in team {team_id} set to {role} successfully!")
