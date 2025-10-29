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
"""Create Cudo Compute VM command."""

import logging

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings

from .. import attach_cudo_compute_client

logger = logging.getLogger(__name__)


@attach_settings
@attach_persona
@attach_cudo_compute_client
async def create_vm(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id", help="Project ID"),
    vm_id: str = typer.Argument(..., help="Unique VM identifier"),
    data_center_id: str = typer.Option(..., "--data-center-id", help="Data center ID"),
    machine_type: str = typer.Option(..., "--machine-type", help="Machine type"),
    boot_disk_image_id: str = typer.Option(..., "--boot-disk-image-id", help="Boot disk image ID"),
    vcpus: int = typer.Option(..., "--vcpus", help="Number of vCPUs"),
    memory_gib: int = typer.Option(..., "--memory-gib", help="Memory in GiB"),
    gpus: int = typer.Option(0, "--gpus", help="Number of GPUs"),
    network_id: str = typer.Option(None, "--network-id", help="Network ID"),
    public_ip: bool = typer.Option(False, "--public-ip", help="Assign public IP"),
    custom_ssh_keys: str = typer.Option(
        None, "--custom-ssh-keys", help="Comma-separated SSH keys"
    ),
) -> None:
    """Create a new Cudo Compute virtual machine."""
    try:
        kwargs = {}
        if network_id:
            kwargs["networkId"] = network_id
        if public_ip:
            kwargs["publicIpConfig"] = {"enabled": True}
        if custom_ssh_keys:
            kwargs["customSshKeys"] = custom_ssh_keys.split(",")

        vm = await ctx.obj.cudo_sdk.create_vm(
            project_id=project_id,
            vm_id=vm_id,
            data_center_id=data_center_id,
            machine_type=machine_type,
            boot_disk_image_id=boot_disk_image_id,
            vcpus=vcpus,
            memory_gib=memory_gib,
            gpus=gpus,
            **kwargs,
        )
        logger.debug(f"[bold green]Success:[/bold green] Created VM '{vm_id}'")
    except Exception as e:
        logger.debug(f"[bold red]Error:[/bold red] Failed to create VM: {e}")
        raise typer.Exit(code=1)

    ctx.obj.formatter.render_get(
        data=vm,
        resource_name=f"Created VM: {vm_id}",
    )
