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

from typing import Any, Dict, List

import typer
from rich.console import Console
from rich.table import Table

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import RenderStepOutput


@handle_abort
@attach_settings
async def list_support_tickets(ctx: typer.Context):
    """List all support tickets."""
    # Get command timing
    command_start_time = getattr(ctx.obj, "command_start_time", None)

    # Check for JSON output mode
    json_output = getattr(ctx.obj, "json_output", False)

    # Mock support ticket data
    tickets: List[Dict[str, Any]] = [
        {
            "ticket_id": "ticket-12345",
            "subject": "Help request",
            "status": "open",
            "priority": "medium",
            "created_at": "2025-01-10T10:00:00Z",
            "updated_at": "2025-01-14T15:30:00Z",
        },
        {
            "ticket_id": "ticket-67890",
            "subject": "Bug report",
            "status": "closed",
            "priority": "high",
            "created_at": "2025-01-05T08:30:00Z",
            "updated_at": "2025-01-12T09:15:00Z",
        },
        {
            "ticket_id": "ticket-11111",
            "subject": "Feature request",
            "status": "in_progress",
            "priority": "low",
            "created_at": "2025-01-12T14:20:00Z",
            "updated_at": "2025-01-15T11:45:00Z",
        },
    ]

    # If JSON mode, bypass all visual rendering
    if json_output:
        result = {"tickets": tickets, "count": len(tickets)}
        RenderStepOutput.json_bypass(result)
        return

    # Regular rendering for non-JSON mode
    step_names = ["Fetching support tickets", "Formatting output"]
    console = Console()

    with RenderStepOutput(
        console=console,
        operation_name="Listing support tickets",
        step_names=step_names,
        json_output=json_output,
        command_start_time=command_start_time,
    ) as renderer:
        renderer.advance("Fetching support tickets", "starting")
        # Simulate fetching
        renderer.advance("Fetching support tickets", "completed")

        renderer.advance("Formatting output", "starting")
        # Simulate formatting
        renderer.advance("Formatting output", "completed")

        # Create and display table
        table = Table(title="Support Tickets")
        table.add_column("Ticket ID", style="cyan", no_wrap=True)
        table.add_column("Subject", style="magenta")
        table.add_column("Status", style="yellow")
        table.add_column("Priority", style="green")
        table.add_column("Created", style="dim")
        table.add_column("Updated", style="dim")

        for ticket in tickets:
            status_color = {
                "open": "[red]open[/red]",
                "closed": "[green]closed[/green]",
                "in_progress": "[yellow]in_progress[/yellow]",
            }.get(ticket["status"], ticket["status"])

            table.add_row(
                ticket["ticket_id"],
                ticket["subject"],
                status_color,
                ticket["priority"],
                ticket["created_at"],
                ticket["updated_at"],
            )

        renderer.table_step(table)
