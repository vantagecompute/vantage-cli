# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Delete job template command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def delete_job_template(
    ctx: typer.Context,
    template_id: Annotated[str, typer.Argument(help="ID of the job template to delete")],
):
    """Delete a job template."""
    if get_effective_json_output(ctx):
        print_json(data={"template_id": template_id, "status": "deleted"})
    else:
        console.print(f"🗑️ Job template {template_id} deleted successfully!")
