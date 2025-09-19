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
"""Get job template command."""

from typing import Annotated

import typer
from rich import print_json

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def get_job_template(
    ctx: typer.Context,
    template_id: Annotated[str, typer.Argument(help="ID of the job template to retrieve")],
):
    """Get details of a specific job template."""
    if get_effective_json_output(ctx):
        print_json(
            data={
                "template_id": template_id,
                "name": "example-template",
                "description": "Example job template",
            }
        )
    else:
        ctx.obj.console.print(f"📋 Job template details for {template_id}")
        ctx.obj.console.print("  Name: example-template")
        ctx.obj.console.print("  Description: Example job template")
