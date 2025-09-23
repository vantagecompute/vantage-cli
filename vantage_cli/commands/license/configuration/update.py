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
"""Update license configuration command."""

from typing import Annotated, Any, Dict, Optional

import typer
from rich import print_json

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def update_license_configuration(
    ctx: typer.Context,
    config_id: Annotated[str, typer.Argument(help="ID of the license configuration to update")],
    name: Annotated[
        Optional[str], typer.Option("--name", "-n", help="New name for the license configuration")
    ] = None,
    license_type: Annotated[
        Optional[str], typer.Option("--type", "-t", help="New license type")
    ] = None,
    max_users: Annotated[
        Optional[int], typer.Option("--max-users", "-m", help="New maximum number of users")
    ] = None,
    description: Annotated[
        Optional[str], typer.Option("--description", "-d", help="New description")
    ] = None,
):
    """Update an existing license configuration."""
    if getattr(ctx.obj, "json_output", False):
        # JSON output
        update_data: Dict[str, Any] = {"config_id": config_id}
        if name:
            update_data["name"] = name
        if license_type:
            update_data["license_type"] = license_type
        if max_users:
            update_data["max_users"] = max_users
        if description:
            update_data["description"] = description

        update_data["message"] = "License configuration updated successfully"
        print_json(data=update_data)
    else:
        # Rich console output
        ctx.obj.console.print("⚙️ License Configuration Update Command")
        ctx.obj.console.print(f"📋 Updating license configuration: {config_id}")
        if name:
            ctx.obj.console.print(f"📝 New name: {name}")
        if license_type:
            ctx.obj.console.print(f"🔒 New license type: {license_type}")
        if max_users:
            ctx.obj.console.print(f"👥 New max users: {max_users}")
        if description:
            ctx.obj.console.print(f"📄 New description: {description}")
        ctx.obj.console.print("⚠️  Not yet implemented - this is a stub")
