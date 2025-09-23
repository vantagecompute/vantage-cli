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
"""List license configurations command."""

import typer
from rich import print_json

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def list_license_configurations(ctx: typer.Context):
    """List all license configurations."""
    if getattr(ctx.obj, "json_output", False):
        # JSON output
        print_json(
            data={
                "configurations": [
                    {
                        "id": "config-1",
                        "name": "Default Configuration",
                        "type": "concurrent",
                        "max_users": 100,
                    },
                    {
                        "id": "config-2",
                        "name": "Enterprise Configuration",
                        "type": "node-locked",
                        "max_users": 500,
                    },
                ],
                "message": "License configurations listed successfully",
            }
        )
    else:
        # Rich console output
        ctx.obj.console.print("⚙️ License Configuration List Command")
        ctx.obj.console.print("📋 This command will list all license configurations")
        ctx.obj.console.print("⚠️  Not yet implemented - this is a stub")
