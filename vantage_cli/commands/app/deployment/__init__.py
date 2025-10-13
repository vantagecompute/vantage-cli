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

from .cleanup import cleanup_orphans
from .delete import delete_deployment
from .get import get_deployment
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
deployment_app.command("get")(get_deployment)
deployment_app.command("delete")(delete_deployment)
deployment_app.command("cleanup-orphans")(cleanup_orphans)


def _register_app_commands():
    """Dynamically register app-specific deployment commands.

    This is called lazily to ensure logging is configured before SDK discovery runs.
    """
    # Import SDK here to avoid module-level initialization
    from vantage_cli.sdk.deployment_app import deployment_app_sdk

    # Dynamically register app-specific deployment commands
    available_apps = deployment_app_sdk.list()
    for app in available_apps:
        try:
            # Skip if module is not loaded
            if app.module is None:
                continue

            # Get all functions from the app module that end with '_command'
            app_commands = {}
            for name, obj in inspect.getmembers(app.module):
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
                    name=app.name,
                    help=f"Commands for {app.name}.",
                    invoke_without_command=True,
                    no_args_is_help=True,
                )

                # Register each command function found in the app
                for command_name, command_func in app_commands.items():
                    # Extract the command name (remove '_command' suffix)
                    cmd_name = command_name.replace("_command", "")
                    app_sub_app.command(cmd_name)(command_func)

                # Register the sub-app with the main deployment app
                deployment_app.add_typer(app_sub_app, name=app.name)

        except Exception as e:
            # Log warning but continue with other apps
            import logging

            logging.warning(f"Failed to register commands for app '{app.name}': {e}")


__all__ = ["deployment_app"]
