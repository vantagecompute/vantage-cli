# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Support ticket management commands."""

from vantage_cli import AsyncTyper

from .create import create_support_ticket
from .delete import delete_support_ticket
from .get import get_support_ticket
from .list import list_support_tickets
from .update import update_support_ticket

support_ticket_app = AsyncTyper(name="support-ticket", help="Manage support tickets")

support_ticket_app.command("create", help="Create a new support ticket")(create_support_ticket)
support_ticket_app.command("delete", help="Delete a support ticket")(delete_support_ticket)
support_ticket_app.command("get", help="Get details of a specific support ticket")(
    get_support_ticket
)
support_ticket_app.command("list", help="List all support tickets")(list_support_tickets)
support_ticket_app.command("update", help="Update a support ticket")(update_support_ticket)
