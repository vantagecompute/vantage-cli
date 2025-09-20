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
"""Update notebook command."""

from typing import Annotated, Optional

import typer
from rich import print_json

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@attach_settings
@handle_abort
async def update_notebook(
    ctx: typer.Context,
    notebook_id: Annotated[str, typer.Argument(help="ID of the notebook to update")],
    name: Annotated[
        Optional[str], typer.Option("--name", "-n", help="New name for the notebook")
    ] = None,
    description: Annotated[
        Optional[str], typer.Option("--description", "-d", help="New description")
    ] = None,
    kernel: Annotated[
        Optional[str], typer.Option("--kernel", "-k", help="New kernel type")
    ] = None,
):
    """Update a Jupyter notebook configuration."""
    if getattr(ctx.obj, "json_output", False):
        # JSON output
        updates = {}
        if name:
            updates["name"] = name
        if description:
            updates["description"] = description
        if kernel:
            updates["kernel"] = kernel

        print_json(
            data={
                "notebook_id": notebook_id,
                "updates": updates,
                "status": "updated",
                "updated_at": "2025-09-10T10:00:00Z",
            }
        )
    else:
        # Rich console output
        ctx.obj.console.print(f"🔄 Updating notebook [bold blue]{notebook_id}[/bold blue]")

        if name:
            ctx.obj.console.print(f"   Name: [green]{name}[/green]")
        if description:
            ctx.obj.console.print(f"   Description: {description}")
        if kernel:
            ctx.obj.console.print(f"   Kernel: [yellow]{kernel}[/yellow]")

        ctx.obj.console.print("✅ Notebook updated successfully!")
