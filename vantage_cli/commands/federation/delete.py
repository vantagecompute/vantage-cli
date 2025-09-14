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
"""Delete federation command."""

import typer
from rich import print_json
from rich.console import Console
from typing_extensions import Annotated

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@attach_settings
@handle_abort
async def delete_federation(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the federation to delete")],
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Force deletion without confirmation")
    ] = False,
):
    """Delete a Vantage federation."""
    console = Console()

    # Determine output format
    use_json = get_effective_json_output(ctx)

    if not force and not use_json:
        # Ask for confirmation
        console.print(f"⚠️  You are about to delete federation '[red]{name}[/red]'")
        console.print("This action cannot be undone!")

        confirm = typer.confirm("Are you sure you want to proceed?")
        if not confirm:
            console.print("Deletion cancelled.")
            return

    if use_json:
        # TODO: Implement actual federation deletion logic
        print_json(
            data={
                "name": name,
                "force": force,
                "status": "deleted",
                "message": "Federation delete command not yet implemented",
            }
        )
    else:
        console.print("🔗 [bold blue]Federation Delete Command[/bold blue]")
        console.print(f"🗑️  Deleting federation: [bold]{name}[/bold]")
        if force:
            console.print("💪 Force deletion enabled")
        console.print("⚠️  [yellow]Not yet implemented - this is a stub[/yellow]")
