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
"""Delete Cudo Compute disk command."""

import logging

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings

from .. import attach_cudo_compute_client

logger = logging.getLogger(__name__)


@attach_settings
@attach_persona
@attach_cudo_compute_client
async def delete_disk(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id", help="Project ID"),
    disk_id: str = typer.Argument(..., help="Disk ID"),
) -> None:
    """Delete a Cudo Compute disk. The disk must be detached first."""
    try:
        await ctx.obj.cudo_sdk.delete_disk(
            project_id=project_id,
            disk_id=disk_id,
        )
    except Exception as e:
        logger.debug(f"[bold red]Error:[/bold red] Failed to delete disk: {e}")
        raise typer.Exit(code=1)

    logger.info(f"Disk '{disk_id}' deleted successfully.")
