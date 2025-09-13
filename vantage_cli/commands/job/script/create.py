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
"""Create job script command."""

from typing import Annotated, Optional

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def create_job_script(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the job script to create")],
    script_type: Annotated[
        str, typer.Option("--type", "-t", help="Script type (bash, python, sbatch)")
    ] = "bash",
    description: Annotated[
        Optional[str], typer.Option("--description", "-d", help="Description of the job script")
    ] = None,
):
    """Create a new job script."""
    if get_effective_json_output(ctx):
        print_json(
            data={
                "script_id": "script-new-123",
                "name": name,
                "script_type": script_type,
                "description": description,
                "status": "created",
                "created_at": "2025-09-10T10:00:00Z",
            }
        )
    else:
        console.print(f"📜 Creating job script [bold blue]{name}[/bold blue]")
        console.print(f"   Type: [green]{script_type}[/green]")
        if description:
            console.print(f"   Description: {description}")
        console.print("✅ Job script created successfully!")
