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
"""Application deployment commands for Vantage CLI."""

from vantage_cli import AsyncTyper

from .deploy import deploy_app
from .list import list_apps

# Create the apps command group
apps_app = AsyncTyper(
    name="apps",
    help="Deploy and manage applications on Vantage compute clusters.",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Register subcommands directly
apps_app.command("list")(list_apps)
apps_app.command("deploy")(deploy_app)

# Add plural alias for list command
apps_app.command("apps", help="List all applications (alias for 'list')")(list_apps)

__all__ = ["apps_app"]
