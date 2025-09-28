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
"""Update license feature command."""

from typing import Annotated, Optional
import json
from pathlib import Path

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.commands.license.client import lm_rest_client


@handle_abort
@attach_settings
async def update_license_feature(
    ctx: typer.Context,
    feature_id: Annotated[str, typer.Argument(help="ID of the license feature to update")],
    name: Annotated[
        Optional[str], typer.Option("--name", "-n", help="New feature name")
    ] = None,
    description: Annotated[
        Optional[str], typer.Option("--description", "-d", help="New feature description")
    ] = None,
    json_file: Annotated[
        Optional[Path], typer.Option("--json-file", "-f", help="JSON file with feature data")
    ] = None,
):
    """Update an existing license feature."""
    client = lm_rest_client(ctx.obj.profile, ctx.obj.settings)
    
    if json_file:
        if not json_file.exists():
            ctx.obj.console.print(f"❌ Error: File {json_file} does not exist")
            raise typer.Exit(1)
        with open(json_file, 'r') as f:
            payload = json.load(f)
    else:
        payload = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if not payload:
            ctx.obj.console.print("❌ Error: No update data provided")
            raise typer.Exit(1)
    
    response = await client.put(f"/features/{feature_id}", json=update_data)
    
    # Use UniversalOutputFormatter for consistent update rendering
    from vantage_cli.render import UniversalOutputFormatter
    formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=ctx.obj.json_output)
    formatter.render_update(
        data=response,
        resource_name="License Feature",
        resource_id=str(feature_id),
        success_message=f"License feature '{response.get('name')}' updated successfully!"
    )