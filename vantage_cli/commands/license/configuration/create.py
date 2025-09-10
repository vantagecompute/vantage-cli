# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Create license configuration command."""

from typing import Annotated, Optional

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def create_license_configuration(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the license configuration to create")],
    license_type: Annotated[
        str, typer.Option("--type", "-t", help="Type of license (concurrent, node-locked, etc.)")
    ],
    max_users: Annotated[
        Optional[int], typer.Option("--max-users", "-m", help="Maximum number of users")
    ] = None,
    description: Annotated[
        Optional[str],
        typer.Option("--description", "-d", help="Description of the license configuration"),
    ] = None,
):
    """Create a new license configuration."""
    if get_effective_json_output(ctx):
        # JSON output
        print_json(
            data={
                "config_id": "config-new-123",
                "name": name,
                "license_type": license_type,
                "max_users": max_users,
                "description": description,
                "status": "created",
                "message": "License configuration created successfully",
            }
        )
    else:
        # Rich console output
        console.print("⚙️ License Configuration Create Command")
        console.print(f"📋 Creating license configuration: {name}")
        console.print(f"🔒 License type: {license_type}")
        if max_users:
            console.print(f"👥 Max users: {max_users}")
        if description:
            console.print(f"📝 Description: {description}")
        console.print("⚠️  Not yet implemented - this is a stub")
