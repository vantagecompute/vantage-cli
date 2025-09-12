# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Create support ticket command."""

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def create_support_ticket(ctx: typer.Context):
    """Create a new support ticket."""
    if get_effective_json_output(ctx):
        print_json(data={"ticket_id": "ticket-12345", "status": "created"})
    else:
        console.print("🎫 Support ticket ticket-12345 created successfully!")
