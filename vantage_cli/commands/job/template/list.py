# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""List job templates command."""

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def list_job_templates(ctx: typer.Context):
    """List all job templates."""
    if get_effective_json_output(ctx):
        print_json(
            data={
                "templates": [
                    {
                        "template_id": "tpl-12345",
                        "name": "example1",
                        "description": "Example template 1",
                    },
                    {
                        "template_id": "tpl-67890",
                        "name": "example2",
                        "description": "Example template 2",
                    },
                ]
            }
        )
    else:
        console.print("📋 Job templates:")
        console.print("  tpl-12345 - example1 (Example template 1)")
        console.print("  tpl-67890 - example2 (Example template 2)")
