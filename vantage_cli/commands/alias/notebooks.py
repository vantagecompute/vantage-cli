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
"""Alias command for notebooks -> notebook list."""

import typer

from vantage_cli.commands.notebook.list import list_notebooks


async def notebooks_command(
    ctx: typer.Context,
):
    """List all notebooks (alias for 'vantage notebook list')."""
    # The notebook list command doesn't support JSON output yet (stub)
    await list_notebooks(ctx)
