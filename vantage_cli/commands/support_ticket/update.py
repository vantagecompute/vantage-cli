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
async def update_support_ticket(
    ctx: typer.Context,
    ticket_id: Annotated[str, typer.Argument(help="ID of the support ticket to update")],
    subject: Annotated[
        Optional[str], typer.Option("--subject", "-s", help="New ticket subject")
    ] = None,
    description: Annotated[
        Optional[str], typer.Option("--description", "-d", help="New ticket description")
    ] = None,
    status: Annotated[
        Optional[str], typer.Option("--status", help="New status (open, in_progress, closed)")
    ] = None,
    priority: Annotated[
        Optional[str],
        typer.Option("--priority", help="New priority (low, medium, high, critical)"),
    ] = None,
):
    """Update a support ticket."""
    # Use UniversalOutputFormatter for consistent output

    try:
        # Use SDK to update support ticket
        logger.debug(f"Updating support ticket '{ticket_id}'")
        ticket = await support_ticket_sdk.update_ticket(
            ctx,
            ticket_id=ticket_id,
            subject=subject,
            description=description,
            status=status,
            priority=priority,
        )

        # Convert SupportTicket object to dict format for the formatter
        ticket_data = {
            "id": ticket.id,
            "subject": ticket.subject,
            "description": ticket.description,
            "status": ticket.status,
            "priority": ticket.priority,
            "owner_email": ticket.owner_email,
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
