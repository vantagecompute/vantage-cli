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
"""Delete Cudo Compute bare-metal machine command."""

import logging

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings

from .. import attach_cudo_compute_client

logger = logging.getLogger(__name__)


@attach_settings
@attach_persona
@attach_cudo_compute_client
async def delete_machine(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id", help="Project ID"),
    machine_id: str = typer.Argument(..., help="Machine ID"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt"),
) -> None:
    """Delete a Cudo Compute bare-metal machine. All data will be lost."""
    if not force:
        confirm = typer.confirm(
            f"Are you sure you want to delete bare-metal machine '{machine_id}'? All data will be lost. This action cannot be undone."
        )
        if not confirm:
            logger.debug("Operation cancelled.")
            raise typer.Exit(code=0)

    try:
        await ctx.obj.cudo_sdk.delete_machine(
            project_id=project_id,
            machine_id=machine_id,
        )
        logger.debug(
            f"[bold green]Success:[/bold green] Deleted bare-metal machine '{machine_id}'"
        )
    except Exception as e:
        logger.debug(f"[bold red]Error:[/bold red] Failed to delete bare-metal machine: {e}")
        raise typer.Exit(code=1)
