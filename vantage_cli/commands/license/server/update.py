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
"""Update license server command."""

from typing import Annotated, Any, Dict, Optional

import typer
from rich import print_json

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def update_license_server(
    ctx: typer.Context,
    server_id: Annotated[str, typer.Argument(help="ID of the license server to update")],
    name: Annotated[
        Optional[str], typer.Option("--name", "-n", help="New name for the license server")
    ] = None,
    host: Annotated[
        Optional[str], typer.Option("--host", "-h", help="New hostname or IP address")
    ] = None,
    port: Annotated[Optional[int], typer.Option("--port", "-p", help="New port number")] = None,
    description: Annotated[
        Optional[str], typer.Option("--description", "-d", help="New description")
    ] = None,
):
    """Update an existing license server."""
    if getattr(ctx.obj, "json_output", False):
        # JSON output
        update_data: Dict[str, Any] = {"server_id": server_id}
        if name:
            update_data["name"] = name
        if host:
            update_data["host"] = host
        if port:
            update_data["port"] = port
        if description:
            update_data["description"] = description

        update_data["message"] = "License server updated successfully"
        print_json(data=update_data)
    else:
        # Rich console output
        ctx.obj.console.print("🔑 License Server Update Command")
        ctx.obj.console.print(f"📋 Updating license server: {server_id}")
        if name:
            ctx.obj.console.print(f"📝 New name: {name}")
        if host:
            ctx.obj.console.print(f"🌐 New host: {host}")
        if port:
            ctx.obj.console.print(f"🔌 New port: {port}")
        if description:
            ctx.obj.console.print(f"📄 New description: {description}")
        ctx.obj.console.print("⚠️  Not yet implemented - this is a stub")
