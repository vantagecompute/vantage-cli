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
"""Federation management commands for Vantage CLI."""

from vantage_cli import AsyncTyper

from .create import create_federation
from .delete import delete_federation
from .get import get_federation
from .list import list_federations
from .update import update_federation

# Create the federation command group
federation_app = AsyncTyper(
    name="federation",
    help="Manage Vantage compute federations for distributed workloads.",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Register subcommands directly
federation_app.command("create")(create_federation)
federation_app.command("delete")(delete_federation)
federation_app.command("get")(get_federation)
federation_app.command("list")(list_federations)
federation_app.command("update")(update_federation)
