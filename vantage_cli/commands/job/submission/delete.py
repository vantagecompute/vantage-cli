# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Delete job submission command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def delete_job_submission(
    ctx: typer.Context,
    submission_id: Annotated[str, typer.Argument(help="ID of the job submission to delete")],
):
    """Delete a job submission."""
    if get_effective_json_output(ctx):
        print_json(data={"submission_id": submission_id, "status": "deleted"})
    else:
        console.print(f"🗑️ Job submission {submission_id} deleted successfully!")
