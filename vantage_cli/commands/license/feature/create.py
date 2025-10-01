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
"""Create license feature command."""

import json
from pathlib import Path
from typing import Annotated, Optional

import typer

from vantage_cli.commands.license.client import lm_rest_client
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def create_license_feature(
    ctx: typer.Context,
    name: Annotated[Optional[str], typer.Option("--name", "-n", help="Feature name")] = None,
    description: Annotated[
        Optional[str], typer.Option("--description", "-d", help="Feature description")
    ] = None,
    json_file: Annotated[
        Optional[Path], typer.Option("--json-file", "-f", help="JSON file with feature data")
    ] = None,
):
    """Create a new license feature."""
    client = lm_rest_client(ctx.obj.profile, ctx.obj.settings)

    if json_file:
        if not json_file.exists():
            ctx.obj.console.print(f"❌ Error: File {json_file} does not exist")
            raise typer.Exit(1)
        with open(json_file, "r") as f:
            payload = json.load(f)
    else:
        if not name:
            ctx.obj.console.print("❌ Error: --name is required when not using --json-file")
            raise typer.Exit(1)
        payload = {"name": name}
        if description:
            payload["description"] = description

    response = await client.post("/features", json=feature_data)

    # Use UniversalOutputFormatter for consistent create rendering
    from vantage_cli.render import UniversalOutputFormatter

    formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=ctx.obj.json_output)
    formatter.render_create(
        data=response,
        resource_name="License Feature",
        success_message=f"License feature '{response.get('name')}' created successfully!",
    )
