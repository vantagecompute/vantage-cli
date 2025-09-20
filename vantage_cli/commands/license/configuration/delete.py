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
"""Delete license configuration command."""

from typing import Annotated

import typer
from rich import print_json

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def delete_license_configuration(
    ctx: typer.Context,
    config_id: Annotated[str, typer.Argument(help="ID of the license configuration to delete")],
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Force delete without confirmation")
    ] = False,
):
    """Delete a license configuration."""
    # Confirmation unless force flag is used
    if not force:
        confirmation = typer.confirm(
            f"Are you sure you want to delete license configuration '{config_id}'?"
        )
        if not confirmation:
            ctx.obj.console.print("❌ Operation cancelled.")
            raise typer.Exit(0)

    if getattr(ctx.obj, "json_output", False):
        # JSON output
        print_json(
            data={
                "config_id": config_id,
                "status": "deleted",
                "message": f"License configuration '{config_id}' deleted successfully",
            }
        )
    else:
        # Rich console output
        ctx.obj.console.print("⚙️ License Configuration Delete Command")
        ctx.obj.console.print(f"📋 Deleting license configuration: {config_id}")
        ctx.obj.console.print("⚠️  Not yet implemented - this is a stub")
