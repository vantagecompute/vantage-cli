# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""List job scripts command."""

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def list_job_scripts(ctx: typer.Context):
    """List all job scripts."""
    if get_effective_json_output(ctx):
        print_json(
            data={
                "scripts": [
                    {"script_id": "script-123", "name": "example-script", "script_type": "bash"}
                ],
                "total": 1,
            }
        )
    else:
        console.print("📜 Job Scripts: script-123 - example-script")
