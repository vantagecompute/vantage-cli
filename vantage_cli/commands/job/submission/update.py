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
"""Update job submission command."""

import json
from pathlib import Path
from typing import Annotated, Optional

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.sdk.job import job_submission_sdk
from vantage_cli.vantage_rest_api_client import attach_vantage_rest_client


@handle_abort
@attach_settings
@attach_persona
@attach_vantage_rest_client(base_path="/jobbergate")
async def update_job_submission(
    ctx: typer.Context,
    submission_id: Annotated[int, typer.Argument(help="ID of the job submission to update")],
    name: Optional[str] = typer.Option(
        None, "--name", "-n", help="New name for the job submission"
    ),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="New description for the job submission"
    ),
    execution_directory: Optional[str] = typer.Option(
        None, "--execution-directory", help="New execution directory"
    ),
    status: Optional[str] = typer.Option(
        None, "--status", help="New status (CREATED, SUBMITTED, REJECTED, DONE, ABORTED)"
    ),
    json_file: Optional[Path] = typer.Option(
        None, "--json-file", "-f", help="Path to JSON file containing update data"
    ),
):
    """Update a job submission."""
    if json_file:
        # Read data from JSON file
        try:
            with open(json_file, "r") as f:
                update_data = json.load(f)
        except Exception as e:
            ctx.obj.console.print(f"❌ Error reading JSON file: {e}", style="red")
            raise typer.Exit(1)
    else:
        # Build update data from command options
        update_data = {}

        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if execution_directory is not None:
            update_data["execution_directory"] = execution_directory
        if status is not None:
            update_data["status"] = status

        if not update_data:
            ctx.obj.console.print(
                "❌ No update fields provided. Use --name, --description, --execution-directory, or --status options.",
                style="red",
            )
            raise typer.Exit(1)

    # Use SDK to update job submission
    result = await job_submission_sdk.update(ctx, str(submission_id), update_data)

    # Use UniversalOutputFormatter for consistent update rendering
    ctx.obj.formatter.render_update(
        data=result,
        resource_name="Job Submission",
        resource_id=str(submission_id),
        success_message=f"Job submission '{result.get('name')}' updated successfully!",
    )
