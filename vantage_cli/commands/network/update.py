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
"""Update network command."""

from typing import Annotated, Optional

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def update_network(
    ctx: typer.Context,
    network_id: Annotated[str, typer.Argument(help="ID of the network to update")],
    name: Annotated[
        Optional[str], typer.Option("--name", "-n", help="New name for the network")
    ] = None,
    description: Annotated[
        Optional[str], typer.Option("--description", "-d", help="New description")
    ] = None,
    enable_dns: Annotated[
        Optional[bool],
        typer.Option("--enable-dns/--disable-dns", help="Enable or disable DNS resolution"),
    ] = None,
):
    """Update a virtual network configuration."""
    # Get command timing
    getattr(ctx.obj, "command_start_time", None)

    # Check for JSON output mode
    getattr(ctx.obj, "json_output", False)

    # Mock result for network update
    result = {
        "status": "success",
        "message": f"Network '{network_id}' updated successfully",
        "network_id": network_id,
        "updates": {"name": name} if name else {},
    }

    # Use UniversalOutputFormatter for consistent update rendering

    ctx.obj.formatter.render_update(
        data=result,
        resource_name="Network",
        resource_id=network_id,
        success_message=f"Network '{network_id}' updated successfully!",
    )
