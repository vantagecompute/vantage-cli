# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Update license configuration command."""

from typing import Annotated, Any, Dict, Optional

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def update_license_configuration(
    ctx: typer.Context,
    config_id: Annotated[str, typer.Argument(help="ID of the license configuration to update")],
    name: Annotated[
        Optional[str], typer.Option("--name", "-n", help="New name for the license configuration")
    ] = None,
    license_type: Annotated[
        Optional[str], typer.Option("--type", "-t", help="New license type")
    ] = None,
    max_users: Annotated[
        Optional[int], typer.Option("--max-users", "-m", help="New maximum number of users")
    ] = None,
    description: Annotated[
        Optional[str], typer.Option("--description", "-d", help="New description")
    ] = None,
):
    """Update an existing license configuration."""
    if get_effective_json_output(ctx):
        # JSON output
        update_data: Dict[str, Any] = {"config_id": config_id}
        if name:
            update_data["name"] = name
        if license_type:
            update_data["license_type"] = license_type
        if max_users:
            update_data["max_users"] = max_users
        if description:
            update_data["description"] = description

        update_data["message"] = "License configuration updated successfully"
        print_json(data=update_data)
    else:
        # Rich console output
        console.print("⚙️ License Configuration Update Command")
        console.print(f"📋 Updating license configuration: {config_id}")
        if name:
            console.print(f"📝 New name: {name}")
        if license_type:
            console.print(f"🔒 New license type: {license_type}")
        if max_users:
            console.print(f"👥 New max users: {max_users}")
        if description:
            console.print(f"📄 New description: {description}")
        console.print("⚠️  Not yet implemented - this is a stub")
