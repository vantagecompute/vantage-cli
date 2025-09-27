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
"""Update license deployment command."""

from typing import Annotated, Optional

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.vantage_rest_api_client import attach_vantage_rest_client


@handle_abort
@attach_settings
@attach_persona
@attach_vantage_rest_client
async def update_license_deployment(
    ctx: typer.Context,
    deployment_id: Annotated[str, typer.Argument(help="ID of the license deployment to update")],
    name: Annotated[
        Optional[str], typer.Option("--name", "-n", help="New name for the deployment")
    ] = None,
    environment: Annotated[
        Optional[str],
        typer.Option("--environment", "-e", help="New environment for the deployment"),
    ] = None,
    nodes: Annotated[Optional[int], typer.Option("--nodes", help="New number of nodes")] = None,
    description: Annotated[
        Optional[str], typer.Option("--description", "-d", help="New description")
    ] = None,
    status: Annotated[
        Optional[str],
        typer.Option("--status", "-s", help="New status (active, inactive, suspended)"),
    ] = None,
):
    """Update a license deployment."""
    # Build updates dict
    updates = {}
    if name:
        updates["name"] = name
    if environment:
        updates["environment"] = environment
    if nodes:
        updates["nodes"] = nodes
    if description:
        updates["description"] = description
    if status:
        updates["status"] = status

    # Stub data - replace with actual API call
    update_result = {
        "deployment_id": deployment_id,
        "updates": updates,
        "status": "updated",
        "updated_at": "2025-09-10T10:00:00Z",
    }

    # Use UniversalOutputFormatter for consistent update rendering
    ctx.obj.formatter.render_update(
        data=update_result,
        resource_name="License Deployment",
        success_message=f"License deployment {deployment_id} updated successfully",
    )
