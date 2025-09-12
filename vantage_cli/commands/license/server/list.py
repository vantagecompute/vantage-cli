# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""List license servers command."""

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def list_license_servers(ctx: typer.Context):
    """List all license servers."""
    if get_effective_json_output(ctx):
        # JSON output
        print_json(
            data={
                "servers": [
                    {"id": "server-1", "name": "Primary License Server", "status": "active"},
                    {"id": "server-2", "name": "Secondary License Server", "status": "standby"},
                ],
                "message": "License servers listed successfully",
            }
        )
    else:
        # Rich console output
        console.print("🔑 License Server List Command")
        console.print("📋 This command will list all license servers")
        console.print("⚠️  Not yet implemented - this is a stub")
