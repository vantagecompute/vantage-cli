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

from vantage_cli.commands.license.client import lm_rest_client
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
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
    client = lm_rest_client(ctx.obj.profile, ctx.obj.settings)

    # Build the request payload
    payload = {
        "name": name,
        "version": version,
        "license_type": license_type,
    }

    if description is not None:
        payload["description"] = description

    response = await client.post("/products", json=product_data)

    # Use UniversalOutputFormatter for consistent create rendering
    from vantage_cli.render import UniversalOutputFormatter

    formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=ctx.obj.json_output)
    formatter.render_create(
        data=response,
        resource_name="License Product",
        success_message=f"License product '{response.get('name')}' created successfully!",
    )
