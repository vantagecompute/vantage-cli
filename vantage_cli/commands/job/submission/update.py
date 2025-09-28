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
from rich import print_json

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.commands.job.client import job_rest_client


@handle_abort
@attach_settings
async def update_job_submission(
    ctx: typer.Context,
    submission_id: Annotated[int, typer.Argument(help="ID of the job submission to update")],
    name: Optional[str] = typer.Option(None, "--name", "-n", help="New name for the job submission"),
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
    # Create REST API client
    client = job_rest_client(ctx.obj.profile, ctx.obj.settings)
    
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
                style="red"
            )
            raise typer.Exit(1)
    
    result = await client.put(f"/job-submissions/{submission_id}", json=update_data)
    
    if ctx.obj.json_output:
        print_json(data=result)
    else:
        ctx.obj.console.print(
            f"✅ Job submission '{result.get('name')}' updated successfully!", 
            style="green"
        )
        ctx.obj.console.print(f"📋 Submission ID: {result.get('id')}")
        ctx.obj.console.print(f"📝 Status: {result.get('status')}")
