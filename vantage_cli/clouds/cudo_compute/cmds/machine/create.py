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
"""Create Cudo Compute bare-metal machine command."""

import logging

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings

from .. import attach_cudo_compute_client

logger = logging.getLogger(__name__)


@attach_settings
@attach_persona
@attach_cudo_compute_client
async def create_machine(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id", help="Project ID"),
    machine_id: str = typer.Argument(..., help="Unique machine identifier"),
    data_center_id: str = typer.Option(..., "--data-center-id", help="Data center ID"),
    machine_type_id: str = typer.Option(..., "--machine-type-id", help="Machine type ID"),
    os: str = typer.Option(..., "--os", help="Operating system"),
    custom_ssh_keys: str = typer.Option(
        None, "--custom-ssh-keys", help="Comma-separated SSH keys"
    ),
    start_script: str = typer.Option(None, "--start-script", help="Start script"),
) -> None:
    """Create a new Cudo Compute bare-metal machine."""
    try:
        kwargs = {}
        if custom_ssh_keys:
            kwargs["customSshKeys"] = custom_ssh_keys.split(",")
        if start_script:
            kwargs["startScript"] = start_script

        machine = await ctx.obj.cudo_sdk.create_machine(
            project_id=project_id,
            machine_id=machine_id,
            data_center_id=data_center_id,
            machine_type_id=machine_type_id,
            os=os,
            **kwargs,
        )
        logger.debug(
            f"[bold green]Success:[/bold green] Created bare-metal machine '{machine_id}'"
        )
    except Exception as e:
        logger.debug(f"[bold red]Error:[/bold red] Failed to create bare-metal machine: {e}")
        raise typer.Exit(code=1)

    ctx.obj.formatter.render_get(
        data=machine,
        resource_name=f"Created Bare-Metal Machine: {machine_id}",
    )
