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
"""Get job template command."""

from typing import Annotated

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
async def get_job_template(
    ctx: typer.Context,
    template_id: Annotated[
        str, typer.Argument(help="ID or identifier of the job template to retrieve")
    ],
):
    """Get details of a specific job template."""
    # Use SDK to fetch job template
    response = await job_template_sdk.get(ctx, template_id)

    if not response:
        ctx.obj.console.print(f"[red]Job template {template_id} not found[/red]")
        raise typer.Exit(1)

    # Use UniversalOutputFormatter for consistent get rendering
    ctx.obj.formatter.render_get(
        data=response, resource_name="Job Template", resource_id=template_id
    )
