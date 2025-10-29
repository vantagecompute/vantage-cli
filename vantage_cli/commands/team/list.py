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

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@attach_settings
@handle_abort
async def list_teams(ctx: typer.Context):
    """List all teams."""
    # Mock team data
    teams = [
        {"team_id": "team-12345", "name": "Development Team", "member_count": 5},
        {"team_id": "team-67890", "name": "QA Team", "member_count": 3},
    ]

    # Use UniversalOutputFormatter for consistent list rendering

    ctx.obj.formatter.render_list(
        data=teams, resource_name="Teams", empty_message="No teams found."
    )
