# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Get job submission command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def get_job_submission(
    ctx: typer.Context,
    submission_id: Annotated[str, typer.Argument(help="ID of the job submission to retrieve")],
):
    """Get details of a specific job submission."""
    if get_effective_json_output(ctx):
        print_json(
            data={"submission_id": submission_id, "script": "example.sh", "status": "running"}
        )
    else:
        console.print(f"📋 Job submission details for {submission_id}")
        console.print("  Script: example.sh")
        console.print("  Status: running")
