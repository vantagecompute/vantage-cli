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
"""Clouds management commands package."""

from vantage_cli import AsyncTyper

from .add import add_command
from .delete import delete_command
from .get import get_command
from .list import list_command
from .update import update_command

cloud_app = AsyncTyper(
    name="cloud",
    help="Manage cloud provider configurations and integrations for your Vantage infrastructure.",
    no_args_is_help=True,
)

# Register all commands
cloud_app.command("add")(add_command)
cloud_app.command("delete")(delete_command)
cloud_app.command("get")(get_command)
cloud_app.command("list")(list_command)
cloud_app.command("update")(update_command)
