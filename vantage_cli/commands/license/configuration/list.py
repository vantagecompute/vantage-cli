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
"""List license configurations command."""

from typing import Annotated, Optional

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.commands.license.client import lm_rest_client


@handle_abort
@attach_settings
async def list_license_configurations(
    ctx: typer.Context,
    search: Annotated[
        Optional[str], typer.Option("--search", "-s", help="Search configurations by name or id")
    ] = None,
    sort: Annotated[
        Optional[str], typer.Option("--sort", help="Sort by field (name, id, created_at)")
    ] = None,
    limit: Annotated[
        Optional[int], typer.Option("--limit", "-l", help="Maximum number of configurations to return")
    ] = None,
    offset: Annotated[
        Optional[int], typer.Option("--offset", "-o", help="Number of configurations to skip")
    ] = None,
):
    """List all license configurations."""
    client = lm_rest_client(ctx.obj.profile, ctx.obj.settings)
    
    params = {}
    if search:
        params["search"] = search
    if sort:
        params["sort"] = sort
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset
        
    configurations = await client.get("/configurations", params=params)
    client.print_json(configurations)
