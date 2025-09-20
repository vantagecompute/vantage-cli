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
"""List command for cloud provider configurations."""

import typer

from vantage_cli.exceptions import handle_abort


@handle_abort
async def list_command(
    ctx: typer.Context,
    command_start_time: float,
) -> None:
    """List all configured cloud providers.

    Displays a list of all cloud provider configurations including their status,
    regions, and basic connection information.

    Args:
        ctx: The Typer context
        command_start_time: Time when the command started execution
    """
    pass
