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
"""Get job submission command."""

from typing import Annotated

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.commands.job.client import job_rest_client
from vantage_cli.render import UniversalOutputFormatter


@handle_abort
@attach_settings
async def get_job_submission(
    ctx: typer.Context,
    submission_id: Annotated[int, typer.Argument(help="ID of the job submission to retrieve")],
):
    """Get details of a specific job submission."""
    # Create REST API client
    client = job_rest_client(ctx.obj.profile, ctx.obj.settings)
    
    response = await client.get(f"/job-submissions/{submission_id}")
    submission_data = response
    
    # Use UniversalOutputFormatter for consistent get rendering
    formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=ctx.obj.json_output)
    formatter.render_get(
        data=submission_data,
        resource_name="Job Submission",
        resource_id=str(submission_id)
    )
