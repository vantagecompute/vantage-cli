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

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def list_apps(
    ctx: typer.Context,
) -> None:
    """List all available applications for deployment."""
    # Import SDK here to avoid module-level initialization
    from vantage_cli.sdk.deployment_app import deployment_app_sdk

    # Get available apps from SDK
    available_apps = deployment_app_sdk.list()
    # Prepare apps data for output
    apps_data = []
    for app in available_apps:
        app_data = {
            "name": app.name,
            "cloud": app.cloud,
            "substrate": app.substrate,
            "module": app.module.__name__
            if app.module and hasattr(app.module, "__name__")
            else "unknown",
        }

        # Try to get description from create function docstring if module is available
        if app.module and hasattr(app.module, "create"):
            func = getattr(app.module, "create")
            if hasattr(func, "__doc__") and func.__doc__:
                app_data["description"] = func.__doc__.strip().split("\n")[0]
            else:
                app_data["description"] = "No documentation available"
        else:
            app_data["description"] = "No create function available"

        apps_data.append(app_data)

    # Use UniversalOutputFormatter for consistent list rendering
    ctx.obj.formatter.render_list(
        data=apps_data, resource_name="Applications", empty_message="No applications found."
    )
