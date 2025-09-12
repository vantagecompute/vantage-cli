# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""List job submissions command."""

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def list_job_submissions(ctx: typer.Context):
    """List all job submissions."""
    if get_effective_json_output(ctx):
        print_json(
            data={
                "submissions": [
                    {"submission_id": "sub-12345", "script": "example1.sh", "status": "running"},
                    {"submission_id": "sub-67890", "script": "example2.sh", "status": "completed"},
                ]
            }
        )
    else:
        console.print("📋 Job submissions:")
        console.print("  sub-12345 - example1.sh (running)")
        console.print("  sub-67890 - example2.sh (completed)")
