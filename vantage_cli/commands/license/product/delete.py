# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Delete license product command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def delete_license_product(
    ctx: typer.Context,
    product_id: Annotated[str, typer.Argument(help="ID of the license product to delete")],
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Force delete without confirmation")
    ] = False,
):
    """Delete a license product."""
    # Confirmation unless force flag is used
    if not force:
        confirmation = typer.confirm(
            f"Are you sure you want to delete license product '{product_id}'?"
        )
        if not confirmation:
            console.print("❌ Operation cancelled.")
            raise typer.Exit(0)

    if get_effective_json_output(ctx):
        # JSON output
        print_json(
            data={
                "product_id": product_id,
                "status": "deleted",
                "message": f"License product '{product_id}' deleted successfully",
            }
        )
    else:
        # Rich console output
        console.print("📦 License Product Delete Command")
        console.print(f"📋 Deleting license product: {product_id}")
        console.print("⚠️  Not yet implemented - this is a stub")
