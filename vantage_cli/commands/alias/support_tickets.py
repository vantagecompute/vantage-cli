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
"""Alias command for support-tickets -> support-ticket list."""

import typer

from vantage_cli.commands.support_ticket.list import list_support_tickets
from vantage_cli.exceptions import handle_abort


@handle_abort
async def support_tickets_command(
    ctx: typer.Context,
):
    """List all support tickets (alias for 'vantage support-ticket list')."""
    await list_support_tickets(ctx)
