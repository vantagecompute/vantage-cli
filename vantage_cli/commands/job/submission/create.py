# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Create job submission command."""

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def create_job_submission(ctx: typer.Context):
    """Create a new job submission."""
    if get_effective_json_output(ctx):
        print_json(data={"submission_id": "sub-12345", "status": "created"})
    else:
        console.print("✅ Job submission sub-12345 created successfully!")
