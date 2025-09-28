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
"""Get license feature command."""

from typing import Annotated

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.commands.license.client import lm_rest_client


@handle_abort
@attach_settings
async def get_license_feature(
    ctx: typer.Context,
    feature_id: Annotated[str, typer.Argument(help="ID of the license feature to get")],
):
    """Get details of a specific license feature."""
    """Get a specific license feature."""
    client = lm_rest_client(ctx.obj.profile, ctx.obj.settings)
    response = await client.get(f"/features/{feature_id}")
    
    # Use UniversalOutputFormatter for consistent get rendering
    from vantage_cli.render import UniversalOutputFormatter
    formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=ctx.obj.json_output)
    formatter.render_get(
        data=response,
        resource_name="License Feature",
        resource_id=str(feature_id)
    )