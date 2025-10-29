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
"""Create license configuration command."""

from typing import Annotated, Optional

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.vantage_rest_api_client import attach_vantage_rest_client


@handle_abort
@attach_settings
@attach_persona
@attach_vantage_rest_client
async def create_license_configuration(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the license configuration to create")],
    license_type: Annotated[
        str, typer.Option("--type", "-t", help="Type of license (concurrent, node-locked, etc.)")
    ],
    max_users: Annotated[
        Optional[int], typer.Option("--max-users", "-m", help="Maximum number of users")
    ] = None,
    description: Annotated[
        Optional[str],
        typer.Option("--description", "-d", help="Description of the license configuration"),
    ] = None,
):
    """Create a new license configuration."""
    # Build the request payload
    payload = {
        "name": name,
        "license_type": license_type,
    }

    if max_users is not None:
        payload["max_users"] = str(max_users)
    if description is not None:
        payload["description"] = description

    response = await ctx.obj.rest_client.post("/configurations", json=payload)

    # Use UniversalOutputFormatter for consistent create rendering

    ctx.obj.formatter.render_create(
        data=response,
        resource_name="License Configuration",
        success_message=f"License configuration '{response.get('name')}' created successfully!",
    )
