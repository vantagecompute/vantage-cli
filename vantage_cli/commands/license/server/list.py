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
"""List license servers command."""

import typer
from rich import print_json

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def list_license_servers(ctx: typer.Context):
    """List all license servers."""
    if getattr(ctx.obj, "json_output", False):
        # JSON output
        print_json(
            data={
                "servers": [
                    {"id": "server-1", "name": "Primary License Server", "status": "active"},
                    {"id": "server-2", "name": "Secondary License Server", "status": "standby"},
                ],
                "message": "License servers listed successfully",
            }
        )
    else:
        # Rich console output
        ctx.obj.console.print("🔑 License Server List Command")
        ctx.obj.console.print("📋 This command will list all license servers")
        ctx.obj.console.print("⚠️  Not yet implemented - this is a stub")
