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

from .deployment import deployment_app
from .deployment.list import list_deployments
from .list import list_apps

app_app = AsyncTyper(
    name="apps",
    help="Manage applications",
    no_args_is_help=True,
)

# Add the list command
app_app.command("list", help="List available applications")(list_apps)

# Add deployment as a subcommand
app_app.add_typer(deployment_app, name="deployment")

# Add deployments as an alias for "deployment list"
app_app.command("deployments", hidden=True)(list_deployments)


# Dynamically register each app as a subcommand
def _register_app_commands():
    """Register all discovered apps as subcommands."""
    from vantage_cli.sdk.deployment_app import deployment_app_sdk

    available_apps = deployment_app_sdk.list()

    for app in available_apps:
        if app.module and hasattr(app.module, "app"):
            # The app module has a typer app - register it as a subcommand
            app_typer = getattr(app.module, "app")
            app_app.add_typer(app_typer, name=app.name)


# Register app commands when this module is imported
_register_app_commands()

__all__ = ["app_app"]
