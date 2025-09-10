# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Get job script command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def get_job_script(
    ctx: typer.Context,
    script_id: Annotated[str, typer.Argument(help="ID of the job script to retrieve")],
):
    """Get details of a specific job script."""
    if get_effective_json_output(ctx):
        print_json(
            data={
                "script_id": script_id,
                "name": "example-script",
                "script_type": "bash",
                "status": "active",
            }
        )
    else:
        console.print(f"📜 Job Script: [bold blue]{script_id}[/bold blue] - example-script")
