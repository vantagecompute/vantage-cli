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
"""List teams command."""

import typer
from rich import print_json

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@attach_settings
@handle_abort
async def list_teams(ctx: typer.Context):
    """List all teams."""
    if getattr(ctx.obj, "json_output", False):
        print_json(
            data={
                "teams": [
                    {"team_id": "team-12345", "name": "Development Team", "member_count": 5},
                    {"team_id": "team-67890", "name": "QA Team", "member_count": 3},
                ]
            }
        )
    else:
        ctx.obj.console.print("👥 Teams:")
        ctx.obj.console.print("  team-12345 - Development Team (5 members)")
        ctx.obj.console.print("  team-67890 - QA Team (3 members)")
