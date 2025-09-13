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
