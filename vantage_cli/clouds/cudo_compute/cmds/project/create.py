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
"""Create Cudo Compute project command."""

import logging

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings

from .. import attach_cudo_compute_client

logger = logging.getLogger(__name__)


@attach_settings
@attach_persona
@attach_cudo_compute_client
async def create_project(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Unique project identifier"),
    billing_account_id: str = typer.Option(..., "--billing-account-id", help="Billing account ID"),
) -> None:
    """Create a new Cudo Compute project."""
    try:
        project_data = {
            "id": project_id,
            "billingAccountId": billing_account_id,
        }
        project = await ctx.obj.cudo_sdk.create_project(project_data=project_data)
        logger.debug(f"[bold green]Success:[/bold green] Created project '{project_id}'")
    except Exception as e:
        logger.debug(f"[bold red]Error:[/bold red] Failed to create project: {e}")
        raise typer.Exit(code=1)

    ctx.obj.formatter.render_get(
        data=project,
        resource_name=f"Created Project: {project_id}",
    )
