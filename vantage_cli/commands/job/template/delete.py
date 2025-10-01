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
from rich import print_json

from vantage_cli.commands.job.client import job_rest_client
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def delete_job_template(
    ctx: typer.Context,
    template_id: Annotated[
        str, typer.Argument(help="ID or identifier of the job template to delete")
    ],
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Delete a job template."""
    # Create REST API client
    client = job_rest_client(ctx.obj.profile, ctx.obj.settings)

    template_name = str(template_id)

    if not yes and not ctx.obj.json_output:
        # Get template info for confirmation
        try:
            response = await client.get(f"/job-script-templates/{template_id}")
            template_data = response
            template_name = template_data.get("name", str(template_id))
        except Exception:
            template_name = str(template_id)

        confirm = typer.confirm(
            f"Are you sure you want to delete job template '{template_name}'? This action cannot be undone."
        )
        if not confirm:
            ctx.obj.console.print("❌ Delete operation cancelled.", style="yellow")
            raise typer.Exit(0)

    await client.delete(f"/job-script-templates/{template_id}")

    # DELETE typically returns empty response on success (204 No Content)
    if ctx.obj.json_output:
        print_json(data={"template_id": template_id, "status": "deleted"})
    else:
        ctx.obj.console.print(
            f"✅ Job template '{template_name}' deleted successfully!", style="green"
        )
