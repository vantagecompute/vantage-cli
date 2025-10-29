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

import logging

import typer
from typing_extensions import Annotated

from vantage_cli.config import attach_graphql_client, attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.sdk.support_ticket.crud import support_ticket_sdk

logger = logging.getLogger(__name__)


@handle_abort
@attach_settings
@attach_graphql_client(base_path="/sos/graphql")
async def get_support_ticket(
    ctx: typer.Context,
    ticket_id: Annotated[str, typer.Argument(help="ID of the support ticket to retrieve")],
):
    """Get details of a specific support ticket."""
    # Use UniversalOutputFormatter for consistent output

    try:
        # Use SDK to get support ticket
        logger.debug(f"Fetching support ticket '{ticket_id}' from SDK")
        ticket = await support_ticket_sdk.get_ticket(ctx, ticket_id)

        if not ticket:
            ctx.obj.formatter.render_error(
                error_message=f"Support ticket '{ticket_id}' not found."
            )
            raise Abort(
                f"Support ticket '{ticket_id}' not found.",
                subject="Ticket Not Found",
                log_message=f"Support ticket '{ticket_id}' not found",
            )

        # Convert SupportTicket object to dict format for the formatter
        ticket_data = {
            "id": ticket.id,
            "title": ticket.title,
            "description": ticket.description,
            "status": ticket.status.value,
            "priority": ticket.priority.value,
            "user_email": ticket.user_email,
            "assigned_to": ticket.assigned_to or "Unassigned",
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at,
        }

        # Use formatter to render the ticket details
        ctx.obj.formatter.render_get(
            data=ticket_data, resource_name="Support Ticket", resource_id=ticket_id
        )

    except Abort:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting support ticket '{ticket_id}': {e}")
        ctx.obj.formatter.render_error(
            error_message=f"An unexpected error occurred while getting support ticket '{ticket_id}'.",
            details={"error": str(e)},
        )
