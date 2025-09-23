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
"""List job templates command."""

import typer
from rich import print_json

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def list_job_templates(ctx: typer.Context):
    """List all job templates."""
    if getattr(ctx.obj, "json_output", False):
        print_json(
            data={
                "templates": [
                    {
                        "template_id": "tpl-12345",
                        "name": "example1",
                        "description": "Example template 1",
                    },
                    {
                        "template_id": "tpl-67890",
                        "name": "example2",
                        "description": "Example template 2",
                    },
                ]
            }
        )
    else:
        ctx.obj.console.print("📋 Job templates:")
        ctx.obj.console.print("  tpl-12345 - example1 (Example template 1)")
        ctx.obj.console.print("  tpl-67890 - example2 (Example template 2)")
