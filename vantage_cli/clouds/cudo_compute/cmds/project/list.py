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
"""List Cudo Compute projects command."""

import logging

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings

from .. import attach_cudo_compute_client

logger = logging.getLogger(__name__)


@attach_settings
@attach_persona
@attach_cudo_compute_client
async def list_projects(
    ctx: typer.Context,
    page_token: str = typer.Option(None, "--page-token", help="Page token for pagination"),
    page_size: int = typer.Option(None, "--page-size", help="Results per page (min 1, max 100)"),
) -> None:
    """List all Cudo Compute projects accessible by the current user."""
    try:
        projects = await ctx.obj.cudo_sdk.list_projects(
            page_token=page_token,
            page_size=page_size,
        )
    except Exception as e:
        logger.debug(f"[bold red]Error:[/bold red] Failed to list projects: {e}")
        raise typer.Exit(code=1)

    if not projects:
        logger.debug("No projects found.")
        return

    # Convert Pydantic models to dicts for the formatter
    projects_data = [p.model_dump() for p in projects]

    ctx.obj.formatter.render_list(
        data=projects_data,
        resource_name="Cudo Compute Projects",
    )
