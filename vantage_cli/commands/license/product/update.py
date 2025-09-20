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
from rich import print_json

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
    if getattr(ctx.obj, "json_output", False):
        # JSON output
        update_data = {"product_id": product_id}
        if name:
            update_data["name"] = name
        if version:
            update_data["version"] = version
        if description:
            update_data["description"] = description
        if license_type:
            update_data["license_type"] = license_type

        update_data["message"] = "License product updated successfully"
        print_json(data=update_data)
    else:
        # Rich console output
        ctx.obj.console.print("📦 License Product Update Command")
        ctx.obj.console.print(f"📋 Updating license product: {product_id}")
        if name:
            ctx.obj.console.print(f"📝 New name: {name}")
        if version:
            ctx.obj.console.print(f"🔢 New version: {version}")
        if description:
            ctx.obj.console.print(f"📄 New description: {description}")
        if license_type:
            ctx.obj.console.print(f"🔒 New license type: {license_type}")
        ctx.obj.console.print("⚠️  Not yet implemented - this is a stub")
