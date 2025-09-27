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
"""Delete license deployment command."""

from typing import Annotated

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.vantage_rest_api_client import attach_vantage_rest_client


@handle_abort
@attach_settings
@attach_persona
@attach_vantage_rest_client
async def delete_license_deployment(
    ctx: typer.Context,
    deployment_id: Annotated[str, typer.Argument(help="ID of the license deployment to delete")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation prompt")] = False,
):
    """Delete a license deployment."""
    if not force:
        if not typer.confirm(f"Are you sure you want to delete deployment {deployment_id}?"):
            ctx.obj.console.print("❌ Deployment deletion cancelled.")
            return

    # Stub data - replace with actual API call
    delete_result = {
        "deployment_id": deployment_id,
        "status": "deleted",
        "deleted_at": "2025-09-10T10:00:00Z",
    }

    # Use UniversalOutputFormatter for consistent delete rendering
    ctx.obj.formatter.render_delete(
        data=delete_result,
        resource_name="License Deployment",
        success_message=f"License deployment {deployment_id} deleted successfully",
    )
