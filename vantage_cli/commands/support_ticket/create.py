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
"""Create support ticket command."""

import logging

import typer
from typing_extensions import Annotated

from vantage_cli.config import attach_graphql_client, attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.sdk.support_ticket.crud import support_ticket_sdk
from vantage_cli.sdk.support_ticket.schema import SeverityLevel

logger = logging.getLogger(__name__)


@handle_abort
@attach_settings
@attach_graphql_client(base_path="/sos/graphql")
async def create_support_ticket(
    ctx: typer.Context,
    title: Annotated[str, typer.Option("--title", "-t", help="Ticket title", prompt=True)],
    description: Annotated[
        str, typer.Option("--description", "-d", help="Ticket description", prompt=True)
    ],
    priority: Annotated[
        str,
        typer.Option("--priority", help="Ticket priority (LOW, MEDIUM, HIGH, CRITICAL)"),
    ] = "MEDIUM",
):
    """Create a new support ticket."""
    # Use UniversalOutputFormatter for consistent output

    try:
        # Validate and convert priority to uppercase enum value
        priority = priority.upper()
        if priority not in [p.value for p in SeverityLevel]:
            raise Abort(
                f"Invalid priority '{priority}'. Must be one of: {', '.join([p.value for p in SeverityLevel])}",
                subject="Invalid Priority",
            )

        # Use SDK to create support ticket
        logger.debug(f"Creating support ticket with title '{title}'")
        ticket = await support_ticket_sdk.create_ticket(
            ctx, title=title, description=description, priority=priority
        )

        # Convert SupportTicket object to dict format for the formatter
        ticket_data = {
            "id": ticket.id,
            "title": ticket.title,
            "description": ticket.description,
            "status": ticket.status.value,
            "priority": ticket.priority.value,
            "user_email": ticket.user_email,
            "created_at": ticket.created_at,
        }

        # Use formatter to render the created ticket
        ctx.obj.formatter.render_get(
            data=ticket_data, resource_name="Support Ticket", resource_id=ticket.id
        )

        if not ctx.obj.json_output:
            ctx.obj.console.print(
                f"\n✅ Support ticket '{ticket.id}' created successfully!", style="bold green"
            )

    except Abort:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating support ticket: {e}")
        ctx.obj.formatter.render_error(
            error_message="An unexpected error occurred while creating the support ticket.",
            details={"error": str(e)},
        )
