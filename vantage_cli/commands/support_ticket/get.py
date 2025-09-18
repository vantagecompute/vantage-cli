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
"""Get support ticket command."""

from typing import Annotated

import typer
from rich import print_json

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def get_support_ticket(
    ctx: typer.Context,
    ticket_id: Annotated[str, typer.Argument(help="ID of the support ticket to retrieve")],
):
    """Get details of a specific support ticket."""
    if get_effective_json_output(ctx):
        print_json(
            data={
                "ticket_id": ticket_id,
                "subject": "Help request",
                "status": "open",
                "priority": "medium",
            }
        )
    else:
        ctx.obj.console.print(f"🎫 Support ticket details for {ticket_id}")
        ctx.obj.console.print("  Subject: Help request")
        ctx.obj.console.print("  Status: open")
        ctx.obj.console.print("  Priority: medium")
