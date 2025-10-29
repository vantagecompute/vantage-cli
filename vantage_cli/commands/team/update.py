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
"""Update team command."""

from typing import Annotated

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@attach_settings
@handle_abort
async def update_team(
    ctx: typer.Context,
    team_id: Annotated[str, typer.Argument(help="ID of the team to update")],
    name: str = typer.Option(None, help="New name of the team"),
    description: str = typer.Option(None, help="New description of the team"),
):
    """Update team settings."""
    # Mock team update result
    result = {
        "team_id": team_id,
        "name": name or "Existing Name",
        "description": description or "Existing Description",
        "updated_at": "2025-09-15T14:30:00Z",
    }

    # Use UniversalOutputFormatter for consistent update rendering

    ctx.obj.formatter.render_update(
        data=result,
        resource_name="Team",
        resource_id=team_id,
        success_message=f"Team '{team_id}' updated successfully!",
    )
