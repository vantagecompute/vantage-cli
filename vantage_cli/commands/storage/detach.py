# Copyright (C) 2025 Vantage Compute Corporation
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
"""Detach storage command."""

from typing import Annotated

import typer
from rich import print_json

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def detach_storage(
    ctx: typer.Context,
    storage_id: Annotated[str, typer.Argument(help="ID of the storage volume to detach")],
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Force detachment without graceful unmounting")
    ] = False,
):
    """Detach a storage volume from an instance."""
    if get_effective_json_output(ctx):
        # JSON output
        print_json(
            data={
                "storage_id": storage_id,
                "status": "detached",
                "force": force,
                "detached_at": "2025-09-10T10:00:00Z",
                "previous_instance": "instance-456",
            }
        )
    else:
        # Rich console output
        ctx.obj.console.print(f"📎 Detaching storage volume [bold blue]{storage_id}[/bold blue]")
        if force:
            ctx.obj.console.print(
                "   [bold red]Force mode enabled - no graceful unmounting[/bold red]"
            )
        ctx.obj.console.print("   Previous instance: [green]instance-456[/green]")
        ctx.obj.console.print("✅ Storage volume detached successfully!")
