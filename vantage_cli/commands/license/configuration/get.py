# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Get license configuration command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def get_license_configuration(
    ctx: typer.Context,
    config_id: Annotated[str, typer.Argument(help="ID of the license configuration to get")],
):
    """Get details of a specific license configuration."""
    if get_effective_json_output(ctx):
        # JSON output
        print_json(
            data={
                "config_id": config_id,
                "name": f"License Configuration {config_id}",
                "type": "concurrent",
                "max_users": 100,
                "status": "active",
                "message": "License configuration details retrieved successfully",
            }
        )
    else:
        # Rich console output
        console.print("⚙️ License Configuration Get Command")
        console.print(f"📋 Getting details for license configuration: {config_id}")
        console.print("⚠️  Not yet implemented - this is a stub")
