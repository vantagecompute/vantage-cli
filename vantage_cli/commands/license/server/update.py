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

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.sdk.license import license_server_sdk
from vantage_cli.vantage_rest_api_client import attach_vantage_rest_client


@handle_abort
@attach_settings
@attach_persona
@attach_vantage_rest_client(base_path="/lm")
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
    # Build the update payload with only provided fields
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if host is not None:
        update_data["host"] = host
    if port is not None:
        update_data["port"] = port
    if description is not None:
        update_data["description"] = description

    # Use SDK to update license server
    response = await license_server_sdk.update(ctx, server_id, update_data)

    # Use UniversalOutputFormatter for consistent update rendering
    ctx.obj.formatter.render_update(
        data=response,
        resource_name="License Server",
        resource_id=str(server_id),
        success_message=f"License server '{response.get('name')}' updated successfully!",
    )
