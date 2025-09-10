# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Get license product command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def get_license_product(
    ctx: typer.Context,
    product_id: Annotated[str, typer.Argument(help="ID of the license product to get")],
):
    """Get details of a specific license product."""
    if get_effective_json_output(ctx):
        # JSON output
        print_json(
            data={
                "product_id": product_id,
                "name": f"License Product {product_id}",
                "version": "1.0.0",
                "status": "active",
                "message": "License product details retrieved successfully",
            }
        )
    else:
        # Rich console output
        console.print("📦 License Product Get Command")
        console.print(f"📋 Getting details for license product: {product_id}")
        console.print("⚠️  Not yet implemented - this is a stub")
