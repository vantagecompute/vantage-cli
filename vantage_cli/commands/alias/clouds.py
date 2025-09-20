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
"""Clouds alias command - maps to 'vantage cloud list'."""

import typer

from vantage_cli.commands.cloud.list import list_command
from vantage_cli.exceptions import handle_abort


@handle_abort
async def clouds_command(
    ctx: typer.Context,
) -> None:
    """List all configured cloud providers.

    This is an alias for 'vantage cloud list'.
    """
    import time

    await list_command(ctx, command_start_time=time.time())


def main():
    """Entry point for direct execution."""
    # This would typically be called through the CLI
    pass


if __name__ == "__main__":
    main()
