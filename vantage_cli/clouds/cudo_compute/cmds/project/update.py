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
"""Update Cudo Compute project command."""

import logging

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings

from .. import attach_cudo_compute_client

logger = logging.getLogger(__name__)


@attach_settings
@attach_persona
@attach_cudo_compute_client
async def update_project(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Project ID"),
    billing_account_id: str = typer.Option(
        ..., "--billing-account-id", help="New billing account ID"
    ),
) -> None:
    """Update a Cudo Compute project."""
    try:
        project = await ctx.obj.cudo_sdk.update_project(
            project_id=project_id,
            billing_account_id=billing_account_id,
        )
        logger.debug(f"[bold green]Success:[/bold green] Updated project '{project_id}'")
    except Exception as e:
        logger.debug(f"[bold red]Error:[/bold red] Failed to update project: {e}")
        raise typer.Exit(code=1)

    ctx.obj.formatter.render_get(
        data=project,
        resource_name=f"Updated Project: {project_id}",
    )
