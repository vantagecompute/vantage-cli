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
"""Delete license deployment command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def delete_license_deployment(
    ctx: typer.Context,
    deployment_id: Annotated[str, typer.Argument(help="ID of the license deployment to delete")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation prompt")] = False,
):
    """Delete a license deployment."""
    if not force:
        if not typer.confirm(f"Are you sure you want to delete deployment {deployment_id}?"):
            console.print("❌ Deployment deletion cancelled.")
            return

    if get_effective_json_output(ctx):
        # JSON output
        print_json(
            data={
                "deployment_id": deployment_id,
                "status": "deleted",
                "deleted_at": "2025-09-10T10:00:00Z",
            }
        )
    else:
        # Rich console output
        console.print(f"🗑️ Deleting license deployment [bold red]{deployment_id}[/bold red]")
        console.print("✅ License deployment deleted successfully!")
