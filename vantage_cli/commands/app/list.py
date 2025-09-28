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
"""List available applications."""

import typer

from vantage_cli.apps.utils import get_available_apps
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def list_apps(
    ctx: typer.Context,
) -> None:
    """List all available applications for deployment."""
    # Get available apps

    # Get available apps
    available_apps = get_available_apps()

    # Prepare apps data for output
    apps_data = []
    for app_name, app_info in available_apps.items():
            app_data = {
                "name": app_name,
                "module": app_info["module"].__name__
                if "module" in app_info and hasattr(app_info["module"], "__name__")
                else "unknown",
            }

            # Try to get description from docstring if available
            if "deploy_function" in app_info:
                func = app_info["deploy_function"]
                if hasattr(func, "__doc__") and func.__doc__:
                    app_data["description"] = func.__doc__.strip().split("\n")[0]
                else:
                    app_data["description"] = "No documentation available"
            else:
                app_data["description"] = "No deploy function available"

            apps_data.append(app_data)

    # Use UniversalOutputFormatter for consistent list rendering
    from vantage_cli.render import UniversalOutputFormatter
    formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=ctx.obj.json_output)
    formatter.render_list(
        data=apps_data,
        resource_name="Applications",
        empty_message="No applications found."
    )
