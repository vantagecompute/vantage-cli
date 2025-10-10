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
"""Create job template command."""

import json
from pathlib import Path
from typing import Optional

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.sdk.job import job_template_sdk
from vantage_cli.vantage_rest_api_client import attach_vantage_rest_client


@handle_abort
@attach_settings
@attach_persona
@attach_vantage_rest_client(base_path="/jobbergate")
async def create_job_template(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name", "-n", help="Name of the job template"),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="Description of the job template"
    ),
    identifier: Optional[str] = typer.Option(
        None, "--identifier", "-i", help="Human-friendly identifier for the job template"
    ),
    json_file: Optional[Path] = typer.Option(
        None, "--json-file", "-f", help="Path to JSON file containing job template data"
    ),
):
    """Create a new job template."""
    if json_file:
        # Read data from JSON file
        try:
            with open(json_file, "r") as f:
                template_data = json.load(f)
        except Exception as e:
            ctx.obj.console.print(f"❌ Error reading JSON file: {e}", style="red")
            raise typer.Exit(1)
    else:
        # Build request data from command options
        template_data = {"name": name}

        if description:
            template_data["description"] = description
        if identifier:
            template_data["identifier"] = identifier

    # Use SDK to create job template
    result = await job_template_sdk.create(ctx, template_data)

    # Use UniversalOutputFormatter for consistent create rendering
    ctx.obj.formatter.render_create(
        data=result,
        resource_name="Job Template",
        success_message=f"Job template '{result.get('name')}' created successfully!",
    )
