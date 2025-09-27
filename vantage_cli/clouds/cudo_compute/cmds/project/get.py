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
"""Get Cudo Compute project command."""

import logging

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings

from .. import attach_cudo_compute_client

logger = logging.getLogger(__name__)


@attach_settings
@attach_persona
@attach_cudo_compute_client
async def get_project(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Project ID"),
) -> None:
    """Get details of a specific Cudo Compute project."""
    try:
        project = await ctx.obj.cudo_sdk.get_project(project_id=project_id)
    except Exception as e:
        logger.debug(f"[bold red]Error:[/bold red] Failed to get project: {e}")
        raise typer.Exit(code=1)

    # Convert Pydantic model to dict for the formatter
    project_data = project.model_dump() if project else {}

    ctx.obj.formatter.render_get(
        data=project_data,
        resource_name=f"Project: {project_id}",
    )
