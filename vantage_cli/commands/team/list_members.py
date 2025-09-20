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
"""List team members command."""

from typing import Annotated

import typer
from rich import print_json

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@attach_settings
@handle_abort
async def list_team_members(
    ctx: typer.Context, team_id: Annotated[str, typer.Argument(help="ID of the team")]
):
    """List all team members."""
    if getattr(ctx.obj, "json_output", False):
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
        ctx.obj.console.print(f"👥 Members of team {team_id}:")
        ctx.obj.console.print("  alice (admin)")
        ctx.obj.console.print("  bob (member)")
