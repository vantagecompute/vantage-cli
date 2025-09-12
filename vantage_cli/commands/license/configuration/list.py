# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""List license configurations command."""

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def list_license_configurations(ctx: typer.Context):
    """List all license configurations."""
    if get_effective_json_output(ctx):
        # JSON output
        print_json(
            data={
                "configurations": [
                    {
                        "id": "config-1",
                        "name": "Default Configuration",
                        "type": "concurrent",
                        "max_users": 100,
                    },
                    {
                        "id": "config-2",
                        "name": "Enterprise Configuration",
                        "type": "node-locked",
                        "max_users": 500,
                    },
                ],
                "message": "License configurations listed successfully",
            }
        )
    else:
        # Rich console output
        console.print("⚙️ License Configuration List Command")
        console.print("📋 This command will list all license configurations")
        console.print("⚠️  Not yet implemented - this is a stub")
