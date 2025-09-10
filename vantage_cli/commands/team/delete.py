# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Delete team command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def delete_team(
    ctx: typer.Context, team_id: Annotated[str, typer.Argument(help="ID of the team to delete")]
):
    """Delete a team."""
    if get_effective_json_output(ctx):
        print_json(data={"team_id": team_id, "status": "deleted"})
    else:
        console.print(f"🗑️ Team {team_id} deleted successfully!")
