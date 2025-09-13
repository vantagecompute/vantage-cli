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
"""Storage management commands for Vantage CLI."""

from vantage_cli import AsyncTyper

from .attach import attach_storage
from .create import create_storage
from .delete import delete_storage
from .detach import detach_storage
from .get import get_storage
from .list import list_storage
from .update import update_storage

# Create the storage command group
storage_app = AsyncTyper(
    name="storage",
    help="Manage storage volumes, disks, and storage configurations for cloud infrastructure.",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Register all commands
storage_app.command("attach")(attach_storage)
storage_app.command("create")(create_storage)
storage_app.command("delete")(delete_storage)
storage_app.command("detach")(detach_storage)
storage_app.command("get")(get_storage)
storage_app.command("list")(list_storage)
storage_app.command("update")(update_storage)
