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
"""App commands for the Vantage CLI."""

from vantage_cli import AsyncTyper

from .list import list_apps

app_app = AsyncTyper(
    name="apps",
    help="Manage applications",
    no_args_is_help=True,
)

# Add the list command
app_app.command("list", help="List available applications")(list_apps)

__all__ = ["app_app"]
