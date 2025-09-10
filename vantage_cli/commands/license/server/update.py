# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Update license server command."""

from typing import Annotated, Any, Dict, Optional

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def update_license_server(
    ctx: typer.Context,
    server_id: Annotated[str, typer.Argument(help="ID of the license server to update")],
    name: Annotated[
        Optional[str], typer.Option("--name", "-n", help="New name for the license server")
    ] = None,
    host: Annotated[
        Optional[str], typer.Option("--host", "-h", help="New hostname or IP address")
    ] = None,
    port: Annotated[Optional[int], typer.Option("--port", "-p", help="New port number")] = None,
    description: Annotated[
        Optional[str], typer.Option("--description", "-d", help="New description")
    ] = None,
):
    """Update an existing license server."""
    if get_effective_json_output(ctx):
        # JSON output
        update_data: Dict[str, Any] = {"server_id": server_id}
        if name:
            update_data["name"] = name
        if host:
            update_data["host"] = host
        if port:
            update_data["port"] = port
        if description:
            update_data["description"] = description

        update_data["message"] = "License server updated successfully"
        print_json(data=update_data)
    else:
        # Rich console output
        console.print("🔑 License Server Update Command")
        console.print(f"📋 Updating license server: {server_id}")
        if name:
            console.print(f"📝 New name: {name}")
        if host:
            console.print(f"🌐 New host: {host}")
        if port:
            console.print(f"🔌 New port: {port}")
        if description:
            console.print(f"📄 New description: {description}")
        console.print("⚠️  Not yet implemented - this is a stub")
