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
"""Create license server command."""

from typing import Annotated, Optional

import typer
from rich import print_json

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def create_license_server(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the license server to create")],
    host: Annotated[
        str, typer.Option("--host", "-h", help="License server hostname or IP address")
    ],
    port: Annotated[
        Optional[int], typer.Option("--port", "-p", help="License server port")
    ] = 27000,
    description: Annotated[
        Optional[str],
        typer.Option("--description", "-d", help="Description of the license server"),
    ] = None,
):
    """Create a new license server."""
    if getattr(ctx.obj, "json_output", False):
        # JSON output
        print_json(
            data={
                "server_id": "server-new-123",
                "name": name,
                "host": host,
                "port": port,
                "description": description,
                "status": "created",
                "message": "License server created successfully",
            }
        )
    else:
        # Rich console output
        ctx.obj.console.print("🔑 License Server Create Command")
        ctx.obj.console.print(f"📋 Creating license server: {name} at {host}:{port}")
        if description:
            ctx.obj.console.print(f"📝 Description: {description}")
        ctx.obj.console.print("⚠️  Not yet implemented - this is a stub")
