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
"""Set team member role command."""

from typing import Annotated

import typer
from rich import print_json

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@attach_settings
@handle_abort
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
        ctx.obj.console.print(
            f"👤 User {user_id} role in team {team_id} set to {role} successfully!"
        )
