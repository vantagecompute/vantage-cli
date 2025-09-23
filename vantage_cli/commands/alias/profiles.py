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
"""Alias command for profiles -> profile list."""

import typer

from vantage_cli.commands.profile.crud import list_profiles
from vantage_cli.exceptions import handle_abort


@handle_abort
def profiles_command(
    ctx: typer.Context,
):
    """List all profiles (alias for 'vantage profile list')."""
    # Extract flags from the AsyncTyper context
    json_output = getattr(ctx.obj, "json_output", False)
    verbose = getattr(ctx.obj, "verbose", False)
    list_profiles(ctx, json_output=json_output, verbose=verbose)
