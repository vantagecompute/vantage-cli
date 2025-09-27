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
"""Update support ticket command."""

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
async def update_support_ticket(
    ctx: typer.Context,
    ticket_id: Annotated[str, typer.Argument(help="ID of the support ticket to update")],
    title: Annotated[Optional[str], typer.Option("--title", "-t", help="New ticket title")] = None,
    description: Annotated[
        Optional[str], typer.Option("--description", "-d", help="New ticket description")
    ] = None,
    status: Annotated[
        Optional[str], typer.Option("--status", help="New status (OPEN, IN_PROGRESS, CLOSED)")
    ] = None,
    priority: Annotated[
        Optional[str],
        typer.Option("--priority", help="New priority (LOW, MEDIUM, HIGH, CRITICAL)"),
    ] = None,
):
    """Update a support ticket."""
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

        # Use SDK to update support ticket
        logger.debug(f"Updating support ticket '{ticket_id}'")
        ticket = await support_ticket_sdk.update_ticket(
            ctx,
            ticket_id=ticket_id,
            title=title,
            description=description,
            status=status,
            priority=priority,
        )

        # Convert SupportTicket object to dict format for the formatter
        ticket_data = {
            "id": ticket.id,
            "title": ticket.title,
            "description": ticket.description,
            "status": ticket.status.value,
            "priority": ticket.priority.value,
            "user_email": ticket.user_email,
            "updated_at": ticket.updated_at,
        }

        # Use formatter to render the updated ticket
        ctx.obj.formatter.render_get(
            data=ticket_data, resource_name="Support Ticket", resource_id=ticket_id
        )

        if not ctx.obj.json_output:
            ctx.obj.console.print(
                f"\n✅ Support ticket '{ticket_id}' updated successfully!", style="bold green"
            )

    except Abort:
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating support ticket '{ticket_id}': {e}")
        ctx.obj.formatter.render_error(
            error_message=f"An unexpected error occurred while updating support ticket '{ticket_id}'.",
            details={"error": str(e)},
        )
