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
"""License booking management commands."""

import typer

from .create import create_booking
from .delete import delete_booking
from .get import get_booking
from .list import list_bookings

app = typer.Typer(help="License booking management commands")

# Register commands
app.command("list", help="List all license bookings")(list_bookings)
app.command("get", help="Get a specific license booking by ID")(get_booking)
app.command("create", help="Create a new license booking")(create_booking)
app.command("delete", help="Delete a license booking")(delete_booking)

__all__ = ["app"]
