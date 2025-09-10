# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Get license server command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def get_license_server(
    ctx: typer.Context,
    server_id: Annotated[str, typer.Argument(help="ID of the license server to get")],
):
    """Get details of a specific license server."""
    if get_effective_json_output(ctx):
        # JSON output
        print_json(
            data={
                "server_id": server_id,
                "name": f"License Server {server_id}",
                "status": "active",
                "message": "License server details retrieved successfully",
            }
        )
    else:
        # Rich console output
        console.print("🔑 License Server Get Command")
        console.print(f"📋 Getting details for license server: {server_id}")
        console.print("⚠️  Not yet implemented - this is a stub")
