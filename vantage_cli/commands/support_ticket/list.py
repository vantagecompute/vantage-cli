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
"""List support tickets command."""

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def list_support_tickets(ctx: typer.Context):
    """List all support tickets."""
    if get_effective_json_output(ctx):
        print_json(
            data={
                "tickets": [
                    {"ticket_id": "ticket-12345", "subject": "Help request", "status": "open"},
                    {"ticket_id": "ticket-67890", "subject": "Bug report", "status": "closed"},
                ]
            }
        )
    else:
        console.print("🎫 Support tickets:")
        console.print("  ticket-12345 - Help request (open)")
        console.print("  ticket-67890 - Bug report (closed)")
