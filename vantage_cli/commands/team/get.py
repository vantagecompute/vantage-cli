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

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@attach_settings
@handle_abort
async def get_team(
    ctx: typer.Context, team_id: Annotated[str, typer.Argument(help="ID of the team to retrieve")]
):
    """Get details of a specific team."""
    # Mock team data
    team = {
        "team_id": team_id,
        "name": "Development Team",
        "description": "Main development team for the project",
        "member_count": 5,
        "created_at": "2025-01-01T00:00:00Z",
    }

    # Use UniversalOutputFormatter for consistent get rendering

    ctx.obj.formatter.render_get(data=team, resource_name="Team", resource_id=team_id)
