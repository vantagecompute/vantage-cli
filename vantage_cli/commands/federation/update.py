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
from typing_extensions import Annotated

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@attach_settings
@handle_abort
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
    # Determine output format using direct context access
    if getattr(ctx.obj, "json_output", False):
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
        ctx.obj.console.print("🔗 [bold blue]Federation Update Command[/bold blue]")
        ctx.obj.console.print(f"✏️  Updating federation: [bold]{name}[/bold]")
        if description:
            ctx.obj.console.print(f"📋 New description: {description}")
        if add_cluster:
            ctx.obj.console.print(f"➕ Adding cluster: {add_cluster}")
        if remove_cluster:
            ctx.obj.console.print(f"➖ Removing cluster: {remove_cluster}")
        ctx.obj.console.print("⚠️  [yellow]Not yet implemented - this is a stub[/yellow]")
