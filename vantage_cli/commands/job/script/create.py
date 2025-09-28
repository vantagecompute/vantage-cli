# Copyright (C) 2025 Vantage Compute Corporation
# This pr    #     # Use UniversalOutputFormatter for consistent create rendering
    formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=ctx.obj.json_output)
    formatter.render_create(
        data=result,
        resource_name="Job Script",
        success_message=f"Job script '{result.get('name')}' created successfully!"
    )ersalOutputFormatter for consistent create rendering
    formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=ctx.obj.json_output)
    formatter.render_create(
        data=result,
        resource_name="Job Script",
        success_message=f"Job script '{result.get('name')}' created successfully!"
    ) free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
"""Create job script command."""

import json
from pathlib import Path
from typing import Optional

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.commands.job.client import job_rest_client
from vantage_cli.render import UniversalOutputFormatter


@handle_abort
@attach_settings
async def create_job_script(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name", "-n", help="Name of the job script"),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="Description of the job script"
    ),
    json_file: Optional[Path] = typer.Option(
        None, "--json-file", "-f", help="Path to JSON file containing job script data"
    ),
):
    """Create a new job script."""
    # Create REST API client
    client = job_rest_client(ctx.obj.profile, ctx.obj.settings)
    
    if json_file:
        # Read data from JSON file
        try:
            with open(json_file, "r") as f:
                script_data = json.load(f)
        except Exception as e:
            ctx.obj.console.print(f"❌ Error reading JSON file: {e}", style="red")
            raise typer.Exit(1)
    else:
        # Build request data from command options
        script_data = {"name": name}
        
        if description:
            script_data["description"] = description
    
    result = await client.post("/job-scripts", json=script_data)
    
    if ctx.obj.json_output:
        print_json(data=result)
    else:
        ctx.obj.console.print(
            f"✅ Job script '{result.get('name')}' created successfully!", 
            style="green"
        )
        ctx.obj.console.print(f"📜 Script ID: {result.get('id')}")
