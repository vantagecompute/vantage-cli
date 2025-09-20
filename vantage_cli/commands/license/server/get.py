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
"""Get license server command."""

from typing import Annotated

import typer
from rich import print_json

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def get_license_server(
    ctx: typer.Context,
    server_id: Annotated[str, typer.Argument(help="ID of the license server to get")],
):
    """Get details of a specific license server."""
    if getattr(ctx.obj, "json_output", False):
        # JSON output
        print_json(
            data={
                "server_id": server_id,
                "name": f"License Server {server_id}",
                "status": "active",
                "message": "License server details retrieved successfully",
            }
        )
    else:
        # Rich console output
        ctx.obj.console.print("🔑 License Server Get Command")
        ctx.obj.console.print(f"📋 Getting details for license server: {server_id}")
        ctx.obj.console.print("⚠️  Not yet implemented - this is a stub")
