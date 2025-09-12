# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Get job template command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def get_job_template(
    ctx: typer.Context,
    template_id: Annotated[str, typer.Argument(help="ID of the job template to retrieve")],
):
    """Get details of a specific job template."""
    if get_effective_json_output(ctx):
        print_json(
            data={
                "template_id": template_id,
                "name": "example-template",
                "description": "Example job template",
            }
        )
    else:
        console.print(f"📋 Job template details for {template_id}")
        console.print("  Name: example-template")
        console.print("  Description: Example job template")
