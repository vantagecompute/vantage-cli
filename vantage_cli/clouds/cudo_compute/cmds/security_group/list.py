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
"""List Cudo Compute security groups command."""

import logging

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings

from .. import attach_cudo_compute_client

logger = logging.getLogger(__name__)


@attach_settings
@attach_persona
@attach_cudo_compute_client
async def list_security_groups(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id", help="Project ID"),
) -> None:
    """List security groups within a Cudo Compute project."""
    try:
        security_groups = await ctx.obj.cudo_sdk.list_security_groups(project_id=project_id)
    except Exception as e:
        logger.debug(f"[bold red]Error:[/bold red] Failed to list security groups: {e}")
        raise typer.Exit(code=1)

    if not security_groups:
        logger.debug(f"No security groups found in project '{project_id}'.")
        return

    # Convert Pydantic models to dicts for the formatter
    security_groups_data = [sg.model_dump() for sg in security_groups]

    ctx.obj.formatter.render_list(
        data=security_groups_data,
        resource_name="Cudo Compute Security Groups",
    )
