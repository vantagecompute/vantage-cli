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

from vantage_cli.commands.job.client import job_rest_client
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import UniversalOutputFormatter


@handle_abort
@attach_settings
async def delete_job_script(
    ctx: typer.Context,
    script_id: Annotated[int, typer.Argument(help="ID of the job script to delete")],
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Delete a job script."""
    # Create REST API client
    client = job_rest_client(ctx.obj.profile, ctx.obj.settings)

    script_name = str(script_id)

    if not yes and not ctx.obj.json_output:
        # Get script info for confirmation
        try:
            response = await client.get(f"/job-scripts/{script_id}")
            script_data = response
            script_name = script_data.get("name", str(script_id))
        except Exception:
            script_name = str(script_id)

        confirm = typer.confirm(
            f"Are you sure you want to delete job script '{script_name}'? This action cannot be undone."
        )
        if not confirm:
            ctx.obj.console.print("❌ Delete operation cancelled.", style="yellow")
            raise typer.Exit(0)

    response = await client.delete(f"/job-scripts/{script_id}")

    # Use UniversalOutputFormatter for consistent delete rendering
    formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=ctx.obj.json_output)
    formatter.render_delete(
        resource_name="Job Script",
        resource_id=str(script_id),
        success_message=f"Job script '{script_name}' deleted successfully!",
    )
