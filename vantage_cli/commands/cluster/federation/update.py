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
"""Update federation command."""

from typing import Optional

import typer
from rich import print_json
from rich.console import Console
from typing_extensions import Annotated

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings


@attach_settings
async def update_federation(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the federation to update")],
    description: Annotated[
        Optional[str],
        typer.Option("--description", "-d", help="New description for the federation"),
    ] = None,
    add_cluster: Annotated[
        Optional[str], typer.Option("--add-cluster", help="Add a cluster to the federation")
    ] = None,
    remove_cluster: Annotated[
        Optional[str],
        typer.Option("--remove-cluster", help="Remove a cluster from the federation"),
    ] = None,
):
    """Update a Vantage federation."""
    console = Console()

    # Determine output format
    # Get JSON flag from context (automatically set by AsyncTyper)
    json_output = getattr(ctx.obj, "json_output", False) if ctx.obj else False
    use_json = get_effective_json_output(ctx, json_output)

    if use_json:
        # TODO: Implement actual federation update logic
        print_json(
            data={
                "name": name,
                "description": description,
                "add_cluster": add_cluster,
                "remove_cluster": remove_cluster,
                "status": "updated",
                "message": "Federation update command not yet implemented",
            }
        )
    else:
        console.print("🔗 [bold blue]Federation Update Command[/bold blue]")
        console.print(f"✏️  Updating federation: [bold]{name}[/bold]")
        if description:
            console.print(f"📋 New description: {description}")
        if add_cluster:
            console.print(f"➕ Adding cluster: {add_cluster}")
        if remove_cluster:
            console.print(f"➖ Removing cluster: {remove_cluster}")
        console.print("⚠️  [yellow]Not yet implemented - this is a stub[/yellow]")
