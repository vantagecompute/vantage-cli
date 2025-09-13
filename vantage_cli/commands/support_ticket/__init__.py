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
