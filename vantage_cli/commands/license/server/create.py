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
"""Create license server command."""

from typing import Annotated, Optional

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.commands.license.client import lm_rest_client


@handle_abort
@attach_settings
async def create_license_server(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the license server to create")],
    host: Annotated[str, typer.Option("--host", "-h", help="Server hostname or IP address")],
    port: Annotated[
        Optional[int], typer.Option("--port", "-p", help="Server port number")
    ] = 27000,
    description: Annotated[
        Optional[str],
        typer.Option("--description", "-d", help="Description of the license server"),
    ] = None,
):
    """Create a new license server."""
    client = lm_rest_client(ctx.obj.profile, ctx.obj.settings)
    
    # Build the request payload
    payload = {
        "name": name,
        "host": host,
        "port": port,
    }
    
    if description is not None:
        payload["description"] = description
    
    response = await client.post("/servers", json=server_data)
    
    # Use UniversalOutputFormatter for consistent create rendering
    from vantage_cli.render import UniversalOutputFormatter
    formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=ctx.obj.json_output)
    formatter.render_create(
        data=response,
        resource_name="License Server",
        success_message=f"License server '{response.get('name')}' created successfully!"
    )
