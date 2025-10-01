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
"""Update license server command."""

from typing import Annotated, Optional

import typer

from vantage_cli.commands.license.client import lm_rest_client
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def update_license_server(
    ctx: typer.Context,
    server_id: Annotated[str, typer.Argument(help="ID of the license server to update")],
    name: Annotated[
        Optional[str], typer.Option("--name", "-n", help="New name for the license server")
    ] = None,
    host: Annotated[
        Optional[str], typer.Option("--host", "-h", help="New hostname or IP address")
    ] = None,
    port: Annotated[Optional[int], typer.Option("--port", "-p", help="New port number")] = None,
    description: Annotated[
        Optional[str], typer.Option("--description", "-d", help="New description")
    ] = None,
):
    """Update an existing license server."""
    client = lm_rest_client(ctx.obj.profile, ctx.obj.settings)

    # Build the update payload with only provided fields
    payload = {}
    if name is not None:
        payload["name"] = name
    if host is not None:
        payload["host"] = host
    if port is not None:
        payload["port"] = port
    if description is not None:
        payload["description"] = description

    response = await client.put(f"/servers/{server_id}", json=update_data)

    # Use UniversalOutputFormatter for consistent update rendering
    from vantage_cli.render import UniversalOutputFormatter

    formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=ctx.obj.json_output)
    formatter.render_update(
        data=response,
        resource_name="License Server",
        resource_id=str(server_id),
        success_message=f"License server '{response.get('name')}' updated successfully!",
    )
