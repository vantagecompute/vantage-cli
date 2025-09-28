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
"""Update job script command."""

import json
from pathlib import Path
from typing import Annotated, Optional

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.commands.job.client import job_rest_client
from vantage_cli.render import UniversalOutputFormatter


@handle_abort
@attach_settings
async def update_job_script(
    ctx: typer.Context,
    script_id: Annotated[int, typer.Argument(help="ID of the job script to update")],
    name: Optional[str] = typer.Option(None, "--name", "-n", help="New name for the job script"),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="New description for the job script"
    ),
    is_archived: Optional[bool] = typer.Option(
        None, "--archived/--not-archived", help="Archive or unarchive the job script"
    ),
    json_file: Optional[Path] = typer.Option(
        None, "--json-file", "-f", help="Path to JSON file containing update data"
    ),
):
    """Update a job script."""
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
        if is_archived is not None:
            update_data["is_archived"] = is_archived
        
        if not update_data:
            ctx.obj.console.print(
                "❌ No update fields provided. Use --name, --description, or --archived options.",
                style="red"
            )
            raise typer.Exit(1)
    
    result = await client.put(f"/job-scripts/{script_id}", json=update_data)
    
    # Use UniversalOutputFormatter for consistent update rendering
    formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=ctx.obj.json_output)
    formatter.render_update(
        data=result,
        resource_name="Job Script",
        resource_id=str(script_id),
        success_message=f"Job script '{result.get('name')}' updated successfully!"
    )
