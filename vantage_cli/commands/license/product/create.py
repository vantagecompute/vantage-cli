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
from rich import print_json

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
    if getattr(ctx.obj, "json_output", False):
        # JSON output
        print_json(
            data={
                "product_id": "product-new-123",
                "name": name,
                "version": version,
                "description": description,
                "license_type": license_type,
                "status": "created",
                "message": "License product created successfully",
            }
        )
    else:
        # Rich console output
        ctx.obj.console.print("📦 License Product Create Command")
        ctx.obj.console.print(f"📋 Creating license product: {name} v{version}")
        ctx.obj.console.print(f"🔒 License type: {license_type}")
        if description:
            ctx.obj.console.print(f"📝 Description: {description}")
        ctx.obj.console.print("⚠️  Not yet implemented - this is a stub")
