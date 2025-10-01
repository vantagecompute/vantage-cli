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

from typing import Optional

import typer
from loguru import logger
from typing_extensions import Annotated

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.render import UniversalOutputFormatter
from vantage_cli.sdk.support_ticket.crud import support_ticket_sdk


@handle_abort
@attach_settings
async def create_support_ticket(
    ctx: typer.Context,
    subject: Annotated[str, typer.Option("--subject", "-s", help="Ticket subject", prompt=True)],
    description: Annotated[
        str, typer.Option("--description", "-d", help="Ticket description", prompt=True)
    ],
    priority: Annotated[
        Optional[str],
        typer.Option("--priority", help="Ticket priority (low, medium, high, critical)"),
    ] = "medium",
):
    """Create a new support ticket."""
    # Use UniversalOutputFormatter for consistent output
    formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=ctx.obj.json_output)

    try:
        # Use SDK to create support ticket
        logger.debug(f"Creating support ticket with subject '{subject}'")
        ticket = await support_ticket_sdk.create_ticket(
            ctx, subject=subject, description=description, priority=priority
        )

        # Convert SupportTicket object to dict format for the formatter
        ticket_data = {
            "id": ticket.id,
            "subject": ticket.subject,
            "description": ticket.description,
            "status": ticket.status,
            "priority": ticket.priority,
            "owner_email": ticket.owner_email,
            "created_at": ticket.created_at,
        }

        # Use formatter to render the created ticket
        formatter.render_get(
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
        formatter.render_error(
            error_message="An unexpected error occurred while creating the support ticket.",
            details={"error": str(e)},
        )
