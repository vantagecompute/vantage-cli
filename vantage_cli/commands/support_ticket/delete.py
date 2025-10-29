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
"""Delete support ticket command."""

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
async def delete_support_ticket(
    ctx: typer.Context,
    ticket_id: Annotated[str, typer.Argument(help="ID of the support ticket to delete")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation prompt")] = False,
):
    """Delete a support ticket."""
    # Use UniversalOutputFormatter for consistent output

    try:
        # Confirm deletion unless --force is used
        if not force and not ctx.obj.json_output:
            confirm = typer.confirm(
                f"Are you sure you want to delete support ticket '{ticket_id}'?"
            )
            if not confirm:
                ctx.obj.console.print("❌ Deletion cancelled.", style="yellow")
                return

        # Use SDK to delete support ticket
        logger.debug(f"Deleting support ticket '{ticket_id}'")
        success = await support_ticket_sdk.delete_ticket(ctx, ticket_id)

        if success:
            if ctx.obj.json_output:
                ctx.obj.formatter.render_get(
                    data={"id": ticket_id, "status": "deleted", "success": True},
                    resource_name="Support Ticket",
                    resource_id=ticket_id,
                )
            else:
                ctx.obj.console.print(
                    f"✅ Support ticket '{ticket_id}' deleted successfully!", style="bold green"
                )
        else:
            raise Abort(
                f"Failed to delete support ticket '{ticket_id}'",
                subject="Deletion Failed",
                log_message="Delete operation returned success=False",
            )

    except Abort:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting support ticket '{ticket_id}': {e}")
        ctx.obj.formatter.render_error(
            error_message=f"An unexpected error occurred while deleting support ticket '{ticket_id}'.",
            details={"error": str(e)},
        )
