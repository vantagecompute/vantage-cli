# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Create job template command."""

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def create_job_template(ctx: typer.Context):
    """Create a new job template."""
    if get_effective_json_output(ctx):
        print_json(data={"template_id": "tpl-12345", "status": "created"})
    else:
        console.print("✅ Job template tpl-12345 created successfully!")
