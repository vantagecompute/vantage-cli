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

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.sdk.license import license_feature_sdk
from vantage_cli.vantage_rest_api_client import attach_vantage_rest_client


@handle_abort
@attach_settings
@attach_persona
@attach_vantage_rest_client(base_path="/lm")
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
    if json_file:
        if not json_file.exists():
            ctx.obj.console.print(f"❌ Error: File {json_file} does not exist")
            raise typer.Exit(1)
        with open(json_file, "r") as f:
            feature_data = json.load(f)
    else:
        if not name:
            ctx.obj.console.print("❌ Error: --name is required when not using --json-file")
            raise typer.Exit(1)
        feature_data = {"name": name}
        if description:
            feature_data["description"] = description

    # Use SDK to create license feature
    response = await license_feature_sdk.create(ctx, feature_data)

    # Use UniversalOutputFormatter for consistent create rendering
    ctx.obj.formatter.render_create(
        data=response,
        resource_name="License Feature",
        success_message=f"License feature '{response.get('name')}' created successfully!",
    )
