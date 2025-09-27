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
"""Delete Cudo Compute project command."""

import asyncio
import logging

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings

from .. import attach_cudo_compute_client

logger = logging.getLogger(__name__)


async def _delete_vms(ctx: typer.Context, project_id: str) -> None:
    """Delete all VMs in a project and wait for cleanup."""
    typer.echo("  Checking for VMs...")
    vms = await ctx.obj.cudo_sdk.list_vms(project_id=project_id)
    if not vms:
        return

    typer.echo(f"  Found {len(vms)} VM(s) to terminate")
    for vm in vms:
        vm_id = vm.id
        typer.echo(f"    Terminating VM: {vm_id}")
        try:
            await ctx.obj.cudo_sdk.terminate_vm(project_id=project_id, vm_id=vm_id)
            typer.echo(f"      ✓ Terminated VM: {vm_id}")
        except Exception as e:
            typer.echo(f"      ⚠ Failed to terminate VM {vm_id}: {e}", err=True)

    # Wait for VMs to be fully terminated and cleaned up
    typer.echo("  Waiting for VM termination and cleanup to complete...")
    max_wait = 60  # Maximum 60 seconds
    wait_interval = 5
    elapsed = 0

    while elapsed < max_wait:
        await asyncio.sleep(wait_interval)
        elapsed += wait_interval

        # Check if VMs are gone
        remaining_vms = await ctx.obj.cudo_sdk.list_vms(project_id=project_id)
        if not remaining_vms:
            typer.echo(f"    ✓ All VMs cleaned up after {elapsed}s")
            break
        typer.echo(
            f"    Still waiting... ({elapsed}s elapsed, {len(remaining_vms)} VM(s) remaining)"
        )

    # Extra wait to ensure NICs are detached
    await asyncio.sleep(3)


async def _delete_disks(ctx: typer.Context, project_id: str) -> None:
    """Delete all disks in a project."""
    typer.echo("  Checking for disks...")
    disks = await ctx.obj.cudo_sdk.list_disks(project_id=project_id)
    if not disks:
        return

    typer.echo(f"  Found {len(disks)} disk(s) to delete")
    for disk in disks:
        disk_id = disk.id
        typer.echo(f"    Deleting disk: {disk_id}")
        try:
            await ctx.obj.cudo_sdk.delete_disk(project_id=project_id, disk_id=disk_id)
            typer.echo(f"      ✓ Deleted disk: {disk_id}")
        except Exception as e:
            typer.echo(f"      ⚠ Failed to delete disk {disk_id}: {e}", err=True)


async def _delete_volumes(ctx: typer.Context, project_id: str) -> None:
    """Delete all volumes in a project."""
    typer.echo("  Checking for volumes...")
    volumes_response = await ctx.obj.cudo_sdk.list_volumes(project_id=project_id)
    volumes = volumes_response.get("volumes", [])
    if not volumes:
        return

    typer.echo(f"  Found {len(volumes)} volume(s) to delete")
    for volume in volumes:
        volume_id = volume.get("id") if isinstance(volume, dict) else volume
        typer.echo(f"    Deleting volume: {volume_id}")
        try:
            await ctx.obj.cudo_sdk.delete_volume(project_id=project_id, volume_id=volume_id)
            typer.echo(f"      ✓ Deleted volume: {volume_id}")
        except Exception as e:
            typer.echo(f"      ⚠ Failed to delete volume {volume_id}: {e}", err=True)


async def _delete_security_groups(ctx: typer.Context, project_id: str) -> None:
    """Delete all security groups in a project."""
    typer.echo("  Checking for security groups...")
    security_groups = await ctx.obj.cudo_sdk.list_security_groups(project_id=project_id)
    if not security_groups:
        return

    typer.echo(f"  Found {len(security_groups)} security group(s) to delete")
    for sg in security_groups:
        sg_id = sg.id
        typer.echo(f"    Deleting security group: {sg_id}")
        try:
            await ctx.obj.cudo_sdk.delete_security_group(
                project_id=project_id, security_group_id=sg_id
            )
            typer.echo(f"      ✓ Deleted security group: {sg_id}")
        except Exception as e:
            typer.echo(f"      ⚠ Failed to delete security group {sg_id}: {e}", err=True)


async def _delete_networks(ctx: typer.Context, project_id: str) -> None:
    """Delete all networks in a project."""
    typer.echo("  Checking for networks...")
    networks = await ctx.obj.cudo_sdk.list_networks(project_id=project_id)
    if not networks:
        return

    typer.echo(f"  Found {len(networks)} network(s) to delete")
    for network in networks:
        network_id = network.id
        typer.echo(f"    Deleting network: {network_id}")
        try:
            await ctx.obj.cudo_sdk.delete_network(project_id=project_id, network_id=network_id)
            typer.echo(f"      ✓ Deleted network: {network_id}")
        except Exception as e:
            typer.echo(f"      ⚠ Failed to delete network {network_id}: {e}", err=True)


async def _delete_all_project_resources(ctx: typer.Context, project_id: str) -> None:
    """Delete all resources in a project in the correct order."""
    await _delete_vms(ctx, project_id)
    await _delete_disks(ctx, project_id)
    await _delete_volumes(ctx, project_id)
    await _delete_security_groups(ctx, project_id)
    await _delete_networks(ctx, project_id)

    # Wait for async deletions to complete
    typer.echo("  Waiting for resource deletions to complete...")
    await asyncio.sleep(5)


async def _delete_project_with_retry(ctx: typer.Context, project_id: str) -> None:
    """Delete the project with retry logic for cleanup delays."""
    typer.echo(f"Deleting project '{project_id}'...")
    max_retries = 5
    retry_delay = 3

    for attempt in range(max_retries):
        try:
            await ctx.obj.cudo_sdk.delete_project(project_id=project_id)
            typer.echo(f"✓ Successfully deleted project '{project_id}'")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                error_msg = str(e)
                if "400" in error_msg:
                    typer.echo(
                        f"  Resource cleanup still in progress, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise
            else:
                typer.echo(f"Error deleting project after {max_retries} attempts: {e}", err=True)
                raise typer.Exit(code=1)



@attach_settings
@attach_persona
@attach_cudo_compute_client
async def delete_project(
    ctx: typer.Context,
    project_id: str = typer.Argument(..., help="Project ID"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt"),
) -> None:
    """Delete a Cudo Compute project. All resources in the project will be deleted first."""
    if not force:
        confirm = typer.confirm(
            f"Are you sure you want to delete project '{project_id}'? All resources in the project will be lost. This action cannot be undone."
        )
        if not confirm:
            typer.echo("Operation cancelled.")
            raise typer.Exit(code=0)

    try:
        # Check if project exists
        projects = await ctx.obj.cudo_sdk.list_projects()
        project = next((p for p in projects if p.id == project_id), None)

        if not project:
            typer.echo(f"Error: Project '{project_id}' not found", err=True)
            raise typer.Exit(code=1)

        resource_count = project.resource_count or 0
        if resource_count > 0:
            typer.echo(f"Project contains {resource_count} resource(s). Deleting all resources...")
            await _delete_all_project_resources(ctx, project_id)

        # Delete the project with retry logic
        await _delete_project_with_retry(ctx, project_id)

    except typer.Exit:
        raise
    except Exception as e:
        typer.echo(f"Error deleting project: {e}", err=True)
        raise typer.Exit(code=1)

