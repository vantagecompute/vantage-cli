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

from typing import Optional

import typer
import logging

logger = logging.getLogger(__name__)
from typing_extensions import Annotated

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.sdk.support_ticket.crud import support_ticket_sdk


@handle_abort
@attach_settings
async def list_support_tickets(
    ctx: typer.Context,
    status: Annotated[
        Optional[str],
        typer.Option("--status", "-s", help="Filter by status (open, in_progress, closed)"),
    ] = None,
    priority: Annotated[
        Optional[str],
        typer.Option("--priority", help="Filter by priority (low, medium, high, critical)"),
    ] = None,
    limit: Annotated[
        Optional[int], typer.Option("--limit", "-l", help="Maximum number of tickets to return")
    ] = None,
):
    """List all support tickets."""
    # Use UniversalOutputFormatter for consistent output

    try:
        # Use the SDK to get support tickets
        logger.debug("Using SDK to list support tickets")
        tickets = await support_ticket_sdk.list_tickets(
            ctx, status=status, priority=priority, limit=limit
        )

        if not tickets:
            ctx.obj.formatter.render_list(
                data=[], resource_name="Support Tickets", empty_message="No support tickets found."
            )
            return

        # Convert SupportTicket objects to dict format for the formatter
        tickets_data = []
        for ticket in tickets:
            ticket_dict = {
                "id": ticket.id,
                "subject": ticket.subject,
                "status": ticket.status,
                "priority": ticket.priority,
                "owner_email": ticket.owner_email,
                "created_at": ticket.created_at,
                "updated_at": ticket.updated_at,
            }
            tickets_data.append(ticket_dict)

        # Use formatter to render the tickets list
        ctx.obj.formatter.render_list(
            data=tickets_data,
            resource_name="Support Tickets",
            empty_message="No support tickets found.",
        )

    except Abort:
        # Re-raise Abort exceptions as they contain user-friendly messages
        raise
    except Exception as e:
        logger.error(f"Unexpected error listing support tickets: {e}")
        ctx.obj.formatter.render_error(
            error_message="An unexpected error occurred while listing support tickets.",
            details={"error": str(e)},
        )
