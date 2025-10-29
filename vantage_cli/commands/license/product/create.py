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
"""Create license product command."""

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
async def create_license_product(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the license product to create")],
    version: Annotated[str, typer.Option("--version", "-v", help="Product version")],
    description: Annotated[
        Optional[str],
        typer.Option("--description", "-d", help="Description of the license product"),
    ] = None,
    license_type: Annotated[
        Optional[str],
        typer.Option("--type", "-t", help="Type of license (concurrent, node-locked, etc.)"),
    ] = "concurrent",
):
    """Create a new license product."""
    # Build the request payload
    product_data = {
        "name": name,
        "version": version,
        "license_type": license_type,
    }

    if description is not None:
        product_data["description"] = description

    # Use SDK to create license product
    response = await license_product_sdk.create(ctx, product_data)

    # Use UniversalOutputFormatter for consistent create rendering
    ctx.obj.formatter.render_create(
        data=response,
        resource_name="License Product",
        success_message=f"License product '{response.get('name')}' created successfully!",
    )
