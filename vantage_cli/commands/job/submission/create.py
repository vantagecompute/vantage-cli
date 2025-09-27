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
"""Create job submission command."""

import json
from pathlib import Path
from typing import List, Optional

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
async def create_job_submission(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name", "-n", help="Name of the job submission"),
    job_script_id: int = typer.Option(..., "--job-script-id", help="ID of the job script to use"),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="Description of the job submission"
    ),
    client_id: Optional[str] = typer.Option(
        None, "--client-id", help="Client ID of the cluster where job should execute"
    ),
    execution_directory: Optional[str] = typer.Option(
        None, "--execution-directory", help="Directory on cluster where job should execute"
    ),
    slurm_job_id: Optional[int] = typer.Option(
        None, "--slurm-job-id", help="SLURM job ID (if already known)"
    ),
    sbatch_arguments: Optional[List[str]] = typer.Option(
        None, "--sbatch-arg", help="SBATCH arguments (can be used multiple times)"
    ),
    json_file: Optional[Path] = typer.Option(
        None, "--json-file", "-f", help="Path to JSON file containing job submission data"
    ),
):
    """Create a new job submission."""
    if json_file:
        # Read data from JSON file
        try:
            with open(json_file, "r") as f:
                submission_data = json.load(f)
        except Exception as e:
            ctx.obj.console.print(f"❌ Error reading JSON file: {e}", style="red")
            raise typer.Exit(1)
    else:
        # Build request data from command options
        submission_data = {
            "name": name,
            "job_script_id": job_script_id,
        }

        if description:
            submission_data["description"] = description
        if client_id:
            submission_data["client_id"] = client_id
        if execution_directory:
            submission_data["execution_directory"] = execution_directory
        if slurm_job_id:
            submission_data["slurm_job_id"] = slurm_job_id
        if sbatch_arguments:
            submission_data["sbatch_arguments"] = sbatch_arguments

    # Use SDK to create job submission
    result = await job_submission_sdk.create(ctx, submission_data)

    # Use UniversalOutputFormatter for consistent create rendering
    ctx.obj.formatter.render_create(
        data=result,
        resource_name="Job Submission",
        success_message=f"Job submission '{result.get('name')}' created successfully!",
    )
