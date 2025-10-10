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
"""Delete job template command."""

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
async def delete_job_template(
    ctx: typer.Context,
    template_id: Annotated[
        str, typer.Argument(help="ID or identifier of the job template to delete")
    ],
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Delete a job template."""
    template_name = str(template_id)

    if not yes and not ctx.obj.json_output:
        # Get template info for confirmation
        try:
            response = await job_template_sdk.get(ctx, template_id)
            if response:
                template_name = response.get("name", str(template_id))
        except Exception:
            template_name = str(template_id)

        confirm = typer.confirm(
            f"Are you sure you want to delete job template '{template_name}'? This action cannot be undone."
        )
        if not confirm:
            ctx.obj.console.print("❌ Delete operation cancelled.", style="yellow")
            raise typer.Exit(0)

    # Use SDK to delete job template
    await job_template_sdk.delete(ctx, template_id)

    # Render output
    ctx.obj.formatter.render_delete(
        data={"template_id": template_id, "status": "deleted"},
        resource_name="Job Template",
        resource_id=str(template_id),
    )
