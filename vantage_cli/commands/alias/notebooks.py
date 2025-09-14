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

from typing import Optional

import typer
from typing_extensions import Annotated

from vantage_cli.commands.notebook.list import list_notebooks
from vantage_cli.exceptions import handle_abort


@handle_abort
async def notebooks_command(
    ctx: typer.Context,
    cluster: Annotated[
        Optional[str], typer.Option("--cluster", "-c", help="Filter by cluster name")
    ] = None,
    status: Annotated[
        Optional[str], typer.Option("--status", "-s", help="Filter by notebook status")
    ] = None,
    kernel: Annotated[
        Optional[str], typer.Option("--kernel", "-k", help="Filter by kernel type")
    ] = None,
    limit: Annotated[
        Optional[int], typer.Option("--limit", "-l", help="Maximum number of notebooks to return")
    ] = None,
):
    """List all notebooks (alias for 'vantage notebook list')."""
    await list_notebooks(ctx, cluster=cluster, status=status, kernel=kernel, limit=limit)
