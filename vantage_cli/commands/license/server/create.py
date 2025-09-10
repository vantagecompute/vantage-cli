# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Create license server command."""

from typing import Annotated, Optional

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def create_license_server(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the license server to create")],
    host: Annotated[
        str, typer.Option("--host", "-h", help="License server hostname or IP address")
    ],
    port: Annotated[
        Optional[int], typer.Option("--port", "-p", help="License server port")
    ] = 27000,
    description: Annotated[
        Optional[str],
        typer.Option("--description", "-d", help="Description of the license server"),
    ] = None,
):
    """Create a new license server."""
    if get_effective_json_output(ctx):
        # JSON output
        print_json(
            data={
                "server_id": "server-new-123",
                "name": name,
                "host": host,
                "port": port,
                "description": description,
                "status": "created",
                "message": "License server created successfully",
            }
        )
    else:
        # Rich console output
        console.print("🔑 License Server Create Command")
        console.print(f"📋 Creating license server: {name} at {host}:{port}")
        if description:
            console.print(f"📝 Description: {description}")
        console.print("⚠️  Not yet implemented - this is a stub")
