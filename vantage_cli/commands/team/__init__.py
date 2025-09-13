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
"""Team management commands."""

from vantage_cli import AsyncTyper

from .add_member import add_team_member
from .create import create_team
from .delete import delete_team
from .get import get_team
from .list import list_teams
from .list_members import list_team_members
from .remove_member import remove_team_member
from .set_role import set_team_member_role
from .update import update_team

team_app = AsyncTyper(name="team", help="Manage teams and memberships")

team_app.command("create", help="Create a new team")(create_team)
team_app.command("delete", help="Delete a team")(delete_team)
team_app.command("get", help="Get details of a specific team")(get_team)
team_app.command("list", help="List all teams")(list_teams)
team_app.command("update", help="Update team settings")(update_team)
team_app.command("add-member", help="Add a member to a team")(add_team_member)
team_app.command("remove-member", help="Remove a member from a team")(remove_team_member)
team_app.command("list-members", help="List all team members")(list_team_members)
team_app.command("set-role", help="Set member role in team")(set_team_member_role)
