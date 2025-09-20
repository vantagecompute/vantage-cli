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
"""Create license configuration command."""

from typing import Annotated, Optional

import typer
from rich import print_json

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def create_license_configuration(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the license configuration to create")],
    license_type: Annotated[
        str, typer.Option("--type", "-t", help="Type of license (concurrent, node-locked, etc.)")
    ],
    max_users: Annotated[
        Optional[int], typer.Option("--max-users", "-m", help="Maximum number of users")
    ] = None,
    description: Annotated[
        Optional[str],
        typer.Option("--description", "-d", help="Description of the license configuration"),
    ] = None,
):
    """Create a new license configuration."""
    if getattr(ctx.obj, "json_output", False):
        # JSON output
        print_json(
            data={
                "config_id": "config-new-123",
                "name": name,
                "license_type": license_type,
                "max_users": max_users,
                "description": description,
                "status": "created",
                "message": "License configuration created successfully",
            }
        )
    else:
        # Rich console output
        ctx.obj.console.print("⚙️ License Configuration Create Command")
        ctx.obj.console.print(f"📋 Creating license configuration: {name}")
        ctx.obj.console.print(f"🔒 License type: {license_type}")
        if max_users:
            ctx.obj.console.print(f"👥 Max users: {max_users}")
        if description:
            ctx.obj.console.print(f"📝 Description: {description}")
        ctx.obj.console.print("⚠️  Not yet implemented - this is a stub")
