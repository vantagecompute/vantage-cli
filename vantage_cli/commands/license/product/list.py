# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""List license products command."""

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def list_license_products(ctx: typer.Context):
    """List all license products."""
    if get_effective_json_output(ctx):
        # JSON output
        print_json(
            data={
                "products": [
                    {
                        "id": "product-1",
                        "name": "Software License A",
                        "version": "1.0.0",
                        "status": "active",
                    },
                    {
                        "id": "product-2",
                        "name": "Software License B",
                        "version": "2.1.0",
                        "status": "active",
                    },
                ],
                "message": "License products listed successfully",
            }
        )
    else:
        # Rich console output
        console.print("📦 License Product List Command")
        console.print("📋 This command will list all license products")
        console.print("⚠️  Not yet implemented - this is a stub")
