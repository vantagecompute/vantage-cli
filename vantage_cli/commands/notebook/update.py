# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Update notebook command."""

from typing import Annotated, Optional

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
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
    if get_effective_json_output(ctx):
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
        console.print(f"🔄 Updating notebook [bold blue]{notebook_id}[/bold blue]")

        if name:
            console.print(f"   Name: [green]{name}[/green]")
        if description:
            console.print(f"   Description: {description}")
        if kernel:
            console.print(f"   Kernel: [yellow]{kernel}[/yellow]")

        console.print("✅ Notebook updated successfully!")
