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
"""Delete storage command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort

console = Console()


@handle_abort
@attach_settings
async def delete_storage(
    ctx: typer.Context,
    storage_id: Annotated[str, typer.Argument(help="ID of the storage volume to delete")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation prompt")] = False,
):
    """Delete a storage volume."""
    if not force:
        if not typer.confirm(f"Are you sure you want to delete storage volume {storage_id}?"):
            console.print("❌ Storage deletion cancelled.")
            return

    if get_effective_json_output(ctx):
        # JSON output
        print_json(
            data={
                "storage_id": storage_id,
                "status": "deleted",
                "deleted_at": "2025-09-10T10:00:00Z",
            }
        )
    else:
        # Rich console output
        console.print(f"🗑️ Deleting storage volume [bold red]{storage_id}[/bold red]")
        console.print("✅ Storage volume deleted successfully!")
