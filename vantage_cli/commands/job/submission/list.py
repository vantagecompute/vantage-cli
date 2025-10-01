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

from vantage_cli.commands.job.client import job_rest_client
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import UniversalOutputFormatter


@handle_abort
@attach_settings
async def list_job_submissions(
    ctx: typer.Context,
    slurm_job_ids: Optional[str] = typer.Option(
        None, "--slurm-job-ids", help="Comma-separated list of SLURM job IDs to filter by"
    ),
    submit_status: Optional[str] = typer.Option(
        None,
        "--submit-status",
        help="Filter by submission status (CREATED, SUBMITTED, REJECTED, DONE, ABORTED)",
    ),
    from_script_id: Optional[int] = typer.Option(
        None, "--from-script-id", help="Filter by job script ID"
    ),
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search job submissions"),
    sort_field: Optional[str] = typer.Option(None, "--sort-field", help="Field to sort by"),
    sort_ascending: bool = typer.Option(
        True, "--sort-ascending/--sort-descending", help="Sort order"
    ),
    user_only: bool = typer.Option(False, "--user-only", help="Show only user's job submissions"),
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

    # Use UniversalOutputFormatter for consistent list rendering
    formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=ctx.obj.json_output)
    formatter.render_list(
        data=submissions_data,
        resource_name="Job Submissions",
        empty_message="No job submissions found.",
    )
