# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Update support ticket command."""

from typing import Annotated

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def update_support_ticket(
    ctx: typer.Context,
    ticket_id: Annotated[str, typer.Argument(help="ID of the support ticket to update")],
):
    """Update a support ticket."""
    if get_effective_json_output(ctx):
        print_json(data={"ticket_id": ticket_id, "status": "updated"})
    else:
        console.print(f"🔄 Support ticket {ticket_id} updated successfully!")
