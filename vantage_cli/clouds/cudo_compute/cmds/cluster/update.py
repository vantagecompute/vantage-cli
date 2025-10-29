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
"""Update Cudo Compute cluster command."""

import logging

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings

from .. import attach_cudo_compute_client

logger = logging.getLogger(__name__)


@attach_settings
@attach_persona
@attach_cudo_compute_client
async def update_cluster(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id", help="Project ID"),
    cluster_id: str = typer.Argument(..., help="Cluster ID"),
    machine_count: int = typer.Option(None, "--machine-count", help="New machine count"),
    custom_ssh_keys: str = typer.Option(
        None, "--custom-ssh-keys", help="Comma-separated SSH keys"
    ),
) -> None:
    """Update a Cudo Compute cluster."""
    try:
        kwargs = {}
        if machine_count is not None:
            kwargs["machineCount"] = machine_count
        if custom_ssh_keys:
            kwargs["customSshKeys"] = custom_ssh_keys.split(",")

        if not kwargs:
            logger.debug("[bold yellow]Warning:[/bold yellow] No update parameters provided")
            raise typer.Exit(code=1)

        cluster = await ctx.obj.cudo_sdk.update_cluster(
            project_id=project_id,
            cluster_id=cluster_id,
            **kwargs,
        )
        logger.debug(f"[bold green]Success:[/bold green] Updated cluster '{cluster_id}'")
    except Exception as e:
        logger.debug(f"[bold red]Error:[/bold red] Failed to update cluster: {e}")
        raise typer.Exit(code=1)

    ctx.obj.formatter.render_get(
        data=cluster,
        resource_name=f"Updated Cluster: {cluster_id}",
    )
