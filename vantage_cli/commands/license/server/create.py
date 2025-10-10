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

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.sdk.license import license_server_sdk
from vantage_cli.vantage_rest_api_client import attach_vantage_rest_client


@handle_abort
@attach_settings
@attach_persona
@attach_vantage_rest_client(base_path="/lm")
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
    # Build the request payload
    server_data = {
        "name": name,
        "host": host,
        "port": port,
    }

    if description is not None:
        server_data["description"] = description

    # Use SDK to create license server
    response = await license_server_sdk.create(ctx, server_data)

    # Use UniversalOutputFormatter for consistent create rendering
    ctx.obj.formatter.render_create(
        data=response,
        resource_name="License Server",
        success_message=f"License server '{response.get('name')}' created successfully!",
    )
