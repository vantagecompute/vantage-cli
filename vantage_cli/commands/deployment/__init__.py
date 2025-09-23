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
"""Deployment management commands for Vantage CLI."""

import inspect

from vantage_cli import AsyncTyper
from vantage_cli.apps.utils import get_available_apps

from .list import list_deployments

# Create the deployment command group
deployment_app = AsyncTyper(
    name="deployment",
    help="Create and manage application deployments on Vantage compute clusters.",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Register main deployment commands
deployment_app.command("list")(list_deployments)

# Dynamically register app-specific deployment commands by discovering command functions in each app
available_apps = get_available_apps()
for app_name, app_info in available_apps.items():
    try:
        app_module = app_info["module"]

        # Get all functions from the app module that end with '_command'
        app_commands = {}
        for name, obj in inspect.getmembers(app_module):
            if (
                inspect.iscoroutinefunction(obj)
                and name.endswith("_command")
                and hasattr(obj, "__annotations__")
            ):
                app_commands[name] = obj

        # Register each command as a subcommand of the app
        if app_commands:
            # Create a sub-app for this application
            app_sub_app = AsyncTyper(
                name=app_name,
                help=f"Commands for {app_name}.",
                invoke_without_command=True,
                no_args_is_help=True,
            )

            # Register each command function found in the app
            for command_name, command_func in app_commands.items():
                # Extract the command name (remove '_command' suffix)
                cmd_name = command_name.replace("_command", "")
                app_sub_app.command(cmd_name)(command_func)

            # Register the sub-app with the main deployment app
            deployment_app.add_typer(app_sub_app, name=app_name)

    except Exception as e:
        # Log warning but continue with other apps
        import logging

        logging.warning(f"Failed to register commands for app '{app_name}': {e}")

__all__ = ["deployment_app"]
