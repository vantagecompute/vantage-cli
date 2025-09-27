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
"""Cloud credential management commands package."""

from vantage_cli import AsyncTyper

from .create import create_command
from .delete import delete_command
from .get import get_command
from .list import list_command
from .update import update_command

credential_app = AsyncTyper(
    name="credential",
    help="Manage cloud provider credentials.",
    no_args_is_help=True,
)

# Register credential commands
credential_app.command("create")(create_command)
credential_app.command("delete")(delete_command)
credential_app.command("get")(get_command)
credential_app.command("list")(list_command)
credential_app.command("update")(update_command)
