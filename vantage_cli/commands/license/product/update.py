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

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.sdk.license import license_product_sdk
from vantage_cli.vantage_rest_api_client import attach_vantage_rest_client


@handle_abort
@attach_settings
@attach_persona
@attach_vantage_rest_client(base_path="/lm")
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
    # Build the update payload with only provided fields
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if version is not None:
        update_data["version"] = version
    if description is not None:
        update_data["description"] = description
    if license_type is not None:
        update_data["license_type"] = license_type

    # Use SDK to update license product
    response = await license_product_sdk.update(ctx, product_id, update_data)

    # Use UniversalOutputFormatter for consistent update rendering
    ctx.obj.formatter.render_update(
        data=response,
        resource_name="License Product",
        resource_id=str(product_id),
        success_message=f"License product '{response.get('name')}' updated successfully!",
    )
