# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Create license product command."""

from typing import Annotated, Optional

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


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
    if get_effective_json_output(ctx):
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
        console.print("📦 License Product Create Command")
        console.print(f"📋 Creating license product: {name} v{version}")
        console.print(f"🔒 License type: {license_type}")
        if description:
            console.print(f"📝 Description: {description}")
        console.print("⚠️  Not yet implemented - this is a stub")
