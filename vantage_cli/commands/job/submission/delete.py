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
"""Delete job submission command."""

from typing import Annotated

import typer
from rich import print_json

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.commands.job.client import job_rest_client


@handle_abort
@attach_settings
async def delete_job_submission(
    ctx: typer.Context,
    submission_id: Annotated[int, typer.Argument(help="ID of the job submission to delete")],
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Delete a job submission."""
    # Create REST API client
    client = job_rest_client(ctx.obj.profile, ctx.obj.settings)
    
    submission_name = str(submission_id)
    
    if not yes and not ctx.obj.json_output:
        # Get submission info for confirmation
        try:
            response = await client.get(f"/job-submissions/{submission_id}")
            submission_data = response
            submission_name = submission_data.get("name", str(submission_id))
        except Exception:
            submission_name = str(submission_id)
        
        confirm = typer.confirm(
            f"Are you sure you want to delete job submission '{submission_name}'? This action cannot be undone."
        )
        if not confirm:
            ctx.obj.console.print("❌ Delete operation cancelled.", style="yellow")
            raise typer.Exit(0)
    
    await client.delete(f"/job-submissions/{submission_id}")
    
    # DELETE typically returns empty response on success (204 No Content)
    if ctx.obj.json_output:
        print_json(data={"submission_id": submission_id, "status": "deleted"})
    else:
        ctx.obj.console.print(
            f"✅ Job submission '{submission_name}' deleted successfully!", 
            style="green"
        )
