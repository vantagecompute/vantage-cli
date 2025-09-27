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

import logging
from typing import Optional

import typer
from typing_extensions import Annotated

from vantage_cli.config import attach_graphql_client, attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.sdk.support_ticket.crud import support_ticket_sdk
from vantage_cli.sdk.support_ticket.schema import SeverityLevel, TicketStatus

logger = logging.getLogger(__name__)


@handle_abort
@attach_settings
@attach_graphql_client(base_path="/sos/graphql")
async def list_support_tickets(
    ctx: typer.Context,
    status: Annotated[
        Optional[str],
        typer.Option("--status", "-s", help="Filter by status (OPEN, IN_PROGRESS, CLOSED)"),
    ] = None,
    priority: Annotated[
        Optional[str],
        typer.Option("--priority", help="Filter by priority (LOW, MEDIUM, HIGH, CRITICAL)"),
    ] = None,
    limit: Annotated[
        Optional[int], typer.Option("--limit", "-l", help="Maximum number of tickets to return")
    ] = None,
):
    """List all support tickets."""
    # Use UniversalOutputFormatter for consistent output

    try:
        # Validate and convert status/priority to uppercase enum values if provided
        if status is not None:
            status = status.upper()
            if status not in [s.value for s in TicketStatus]:
                raise Abort(
                    f"Invalid status '{status}'. Must be one of: {', '.join([s.value for s in TicketStatus])}",
                    subject="Invalid Status",
                )

        if priority is not None:
            priority = priority.upper()
            if priority not in [p.value for p in SeverityLevel]:
                raise Abort(
                    f"Invalid priority '{priority}'. Must be one of: {', '.join([p.value for p in SeverityLevel])}",
                    subject="Invalid Priority",
                )

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
                "title": ticket.title,
                "status": ticket.status.value,
                "priority": ticket.priority.value,
                "user_email": ticket.user_email,
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
