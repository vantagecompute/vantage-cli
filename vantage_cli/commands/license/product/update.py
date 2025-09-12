# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Update license product command."""

from typing import Annotated, Optional

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


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
    if get_effective_json_output(ctx):
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
        console.print("📦 License Product Update Command")
        console.print(f"📋 Updating license product: {product_id}")
        if name:
            console.print(f"📝 New name: {name}")
        if version:
            console.print(f"🔢 New version: {version}")
        if description:
            console.print(f"📄 New description: {description}")
        if license_type:
            console.print(f"🔒 New license type: {license_type}")
        console.print("⚠️  Not yet implemented - this is a stub")
