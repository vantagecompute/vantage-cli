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
"""Delete job script command."""

from typing import Annotated

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.sdk.job import job_script_sdk
from vantage_cli.vantage_rest_api_client import attach_vantage_rest_client


@handle_abort
@attach_settings
@attach_persona
@attach_vantage_rest_client(base_path="/jobbergate")
async def delete_job_script(
    ctx: typer.Context,
    script_id: Annotated[int, typer.Argument(help="ID of the job script to delete")],
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Delete a job script."""
    script_name = str(script_id)

    if not yes and not ctx.obj.json_output:
        # Get script info for confirmation
        try:
            response = await job_script_sdk.get(ctx, str(script_id))
            if response:
                script_name = response.get("name", str(script_id))
        except Exception:
            script_name = str(script_id)

        confirm = typer.confirm(
            f"Are you sure you want to delete job script '{script_name}'? This action cannot be undone."
        )
        if not confirm:
            ctx.obj.console.print("❌ Delete operation cancelled.", style="yellow")
            raise typer.Exit(0)

    # Use SDK to delete job script
    await job_script_sdk.delete(ctx, str(script_id))

    # Use UniversalOutputFormatter for consistent delete rendering
    ctx.obj.formatter.render_delete(
        resource_name="Job Script",
        resource_id=str(script_id),
        success_message=f"Job script '{script_name}' deleted successfully!",
    )
