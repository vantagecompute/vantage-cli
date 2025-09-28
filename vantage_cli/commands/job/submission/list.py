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
"""List job submissions command."""

from typing import Optional

import typer
from rich import print_json
from rich.table import Table

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.commands.job.client import job_rest_client


@handle_abort
@attach_settings
async def list_job_submissions(
    ctx: typer.Context,
    slurm_job_ids: Optional[str] = typer.Option(
        None, "--slurm-job-ids", help="Comma-separated list of SLURM job IDs to filter by"
    ),
    submit_status: Optional[str] = typer.Option(
        None, "--submit-status", help="Filter by submission status (CREATED, SUBMITTED, REJECTED, DONE, ABORTED)"
    ),
    from_script_id: Optional[int] = typer.Option(
        None, "--from-script-id", help="Filter by job script ID"
    ),
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search job submissions"),
    sort_field: Optional[str] = typer.Option(
        None, "--sort-field", help="Field to sort by"
    ),
    sort_ascending: bool = typer.Option(
        True, "--sort-ascending/--sort-descending", help="Sort order"
    ),
    user_only: bool = typer.Option(
        False, "--user-only", help="Show only user's job submissions"
    ),
    include_archived: bool = typer.Option(
        False, "--include-archived", help="Include archived job submissions"
    ),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum number of results"),
    offset: int = typer.Option(0, "--offset", "-o", help="Number of results to skip"),
):
    """List all job submissions."""
    # Create REST API client
    client = job_rest_client(ctx.obj.profile, ctx.obj.settings)
    
    # Build query parameters
    params = {
        "page": (offset // limit) + 1,
        "size": limit,
        "sort_ascending": sort_ascending,
        "user_only": user_only,
        "include_archived": include_archived,
    }
    
    if slurm_job_ids:
        params["slurm_job_ids"] = slurm_job_ids
    if submit_status:
        params["submit_status"] = submit_status
    if from_script_id:
        params["from_job_script_id"] = from_script_id
    if search:
        params["search"] = search
    if sort_field:
        params["sort_field"] = sort_field
    
    response = await client.get("/job-submissions", params=params)
    submissions_data = response
    
    if ctx.obj.json_output:
        print_json(data=submissions_data)
    else:
        submissions = submissions_data.get("items", [])
        if not submissions:
            ctx.obj.console.print("📋 No job submissions found.")
            return
        
        table = Table(title="Job Submissions", show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan", min_width=8)
        table.add_column("Name", style="green", min_width=20)
        table.add_column("Owner", style="blue", min_width=15)
        table.add_column("Description", style="white", min_width=30)
        table.add_column("Script ID", style="yellow", min_width=10)
        table.add_column("SLURM ID", style="purple", min_width=10)
        table.add_column("Status", style="red", min_width=10)
        table.add_column("Created", style="dim", min_width=10)
        
        for submission in submissions:
            table.add_row(
                str(submission.get("id", "")),
                submission.get("name", ""),
                submission.get("owner_email", ""),
                submission.get("description", "") or "N/A",
                str(submission.get("job_script_id", "")) if submission.get("job_script_id") else "N/A",
                str(submission.get("slurm_job_id", "")) if submission.get("slurm_job_id") else "N/A",
                submission.get("status", ""),
                submission.get("created_at", "")[:10] if submission.get("created_at") else "",
            )
        
        ctx.obj.console.print(table)
        
        # Show pagination info
        total = submissions_data.get("total", 0)
        current_page = submissions_data.get("page", 1)
        pages = submissions_data.get("pages", 1)
        
        ctx.obj.console.print(f"\nPage {current_page} of {pages} (Total: {total})")
