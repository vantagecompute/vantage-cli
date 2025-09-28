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
"""List license servers command."""

from typing import Annotated, Optional

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.commands.license.client import lm_rest_client


@handle_abort
@attach_settings
async def list_license_servers(
    ctx: typer.Context,
    search: Annotated[
        Optional[str], typer.Option("--search", "-s", help="Search term for filtering servers")
    ] = None,
    sort: Annotated[
        Optional[str], typer.Option("--sort", help="Sort field for ordering results")
    ] = None,
    limit: Annotated[
        Optional[int], typer.Option("--limit", "-l", help="Maximum number of results to return")
    ] = None,
    offset: Annotated[
        Optional[int], typer.Option("--offset", "-o", help="Number of results to skip")
    ] = None,
):
    """List all license servers."""
    client = lm_rest_client(ctx.obj.profile, ctx.obj.settings)
    
    params = {}
    if search:
        params["search"] = search
    if sort:
        params["sort"] = sort
    if limit:
        params["limit"] = limit
    if offset:
        params["offset"] = offset
    
    response = await client.get("/servers", params=params)
    
    # Use UniversalOutputFormatter for consistent list rendering
    from vantage_cli.render import UniversalOutputFormatter
    formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=ctx.obj.json_output)
    formatter.render_list(
        data=response,
        resource_name="License Servers",
        empty_message="No license servers found."
    )
