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
"""List available applications for deployment."""

import typer
from rich.console import Console
from rich.table import Table

from vantage_cli.commands.cluster.utils import get_available_apps
from vantage_cli.config import attach_settings
from vantage_cli.format import render_json

console = Console()


@attach_settings
async def list_apps(
    ctx: typer.Context,
) -> None:
    """List all available applications for deployment."""
    # Get JSON flag from context (automatically set by AsyncTyper)
    json_output = getattr(ctx.obj, "json_output", False) if ctx.obj else False

    try:
        # Get available apps
        available_apps = get_available_apps()

        if json_output:
            # Format for JSON output
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
                        app_data["description"] = "No description available"
                else:
                    app_data["description"] = "No deploy function available"

                apps_data.append(app_data)

            render_json({"apps": apps_data})
            return

        # Rich table output
        if not available_apps:
            console.print("[yellow]No applications found.[/yellow]")
            return

        table = Table(
            title="Available Applications", show_header=True, header_style="bold magenta"
        )
        table.add_column("App Name", style="cyan", width=20)
        table.add_column("Module", style="green", width=30)
        table.add_column("Description", style="white", width=50)

        for app_name, app_info in available_apps.items():
            # Get module name
            module_name = "unknown"
            if "module" in app_info:
                module_name = (
                    app_info["module"].__name__
                    if hasattr(app_info["module"], "__name__")
                    else "unknown"
                )

            # Get description from docstring
            description = "No description available"
            if "deploy_function" in app_info:
                func = app_info["deploy_function"]
                if hasattr(func, "__doc__") and func.__doc__:
                    # Get first line of docstring
                    description = func.__doc__.strip().split("\n")[0]
                else:
                    description = "No description available"
            else:
                description = "No deploy function available"

            table.add_row(app_name, module_name, description)

        console.print(table)
        console.print(f"\n[bold]Found {len(available_apps)} application(s)[/bold]")

    except Exception as e:
        console.print(f"[bold red]Error listing applications: {e}[/bold red]")
        raise typer.Exit(1)
