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
