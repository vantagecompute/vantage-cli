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
"""Update license product command."""

from typing import Annotated, Optional

import typer

from vantage_cli.commands.license.client import lm_rest_client
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def update_license_product(
    ctx: typer.Context,
    product_id: Annotated[str, typer.Argument(help="ID of the license product to update")],
    name: Annotated[
        Optional[str], typer.Option("--name", "-n", help="New name for the license product")
    ] = None,
    version: Annotated[Optional[str], typer.Option("--version", "-v", help="New version")] = None,
    description: Annotated[
        Optional[str], typer.Option("--description", "-d", help="New description")
    ] = None,
    license_type: Annotated[
        Optional[str], typer.Option("--type", "-t", help="New license type")
    ] = None,
):
    """Update an existing license product."""
    client = lm_rest_client(ctx.obj.profile, ctx.obj.settings)

    # Build the update payload with only provided fields
    payload = {}
    if name is not None:
        payload["name"] = name
    if version is not None:
        payload["version"] = version
    if description is not None:
        payload["description"] = description
    if license_type is not None:
        payload["license_type"] = license_type

    response = await client.put(f"/products/{product_id}", json=update_data)

    # Use UniversalOutputFormatter for consistent update rendering
    from vantage_cli.render import UniversalOutputFormatter

    formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=ctx.obj.json_output)
    formatter.render_update(
        data=response,
        resource_name="License Product",
        resource_id=str(product_id),
        success_message=f"License product '{response.get('name')}' updated successfully!",
    )
