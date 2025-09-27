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
"""Multipass singlenode application support."""

import logging
import os
import subprocess
from pathlib import Path
from shutil import which
from typing import Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from vantage_cli.clouds.common import (
    create_deployment_with_init_status,
    generate_dev_cluster_data,
)
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.sdk.cloud.crud import cloud_sdk
from vantage_cli.sdk.cluster.schema import Cluster, VantageClusterContext
from vantage_cli.sdk.deployment.crud import deployment_sdk
from vantage_cli.sdk.deployment.schema import Deployment

from .constants import (
    APP_NAME,
    MULTIPASS_CLOUD_IMAGE_DEST,
    MULTIPASS_CLOUD_IMAGE_LOCAL,
    MULTIPASS_CLOUD_IMAGE_URL,
    SUBSTRATE,
)
from .constants import (
    CLOUD as CLOUD_LOCALHOST,
)
from .render import success_create_message
from .templates import CloudInitTemplate
from .utils import check_multipass_available

logger = logging.getLogger(__name__)


def _prepare_shared_directory(verbose: bool, console: Console) -> Path:
    """Prepare shared directory for VM mounting."""
    shared_dir = Path.home() / "multipass-singlenode" / "shared"
    shared_dir.mkdir(parents=True, exist_ok=True)
    shared_dir.chmod(0o755)  # Fixed: use Path.chmod instead of shutil.chmod

    if verbose:
        console.print(f"Prepared shared directory: {shared_dir}")

    return shared_dir


def _generate_cloud_init_configuration(
    vantage_cluster_ctx: VantageClusterContext,
) -> tuple[str, str]:
    """Generate cloud-init configuration and determine image origin.

    Args:
        vantage_cluster_ctx: VantageClusterContext with cluster details

    Returns:
        Tuple of (cloud_init_config, image_origin)
    """
    # Use a standard Ubuntu image for now since the custom Vantage image may not be available
    image_origin = MULTIPASS_CLOUD_IMAGE_URL
    if MULTIPASS_CLOUD_IMAGE_LOCAL.exists():
        image_origin = f"file://{MULTIPASS_CLOUD_IMAGE_LOCAL}"
    elif MULTIPASS_CLOUD_IMAGE_DEST.exists():
        image_origin = f"file://{MULTIPASS_CLOUD_IMAGE_DEST}"
    # Note: Fallback to standard Ubuntu image if custom image not available

    # Generate cloud-init configuration using template engine
    cloud_init_template = CloudInitTemplate()
    cloud_init_config = cloud_init_template.generate_multipass_config(vantage_cluster_ctx)

    return cloud_init_config, image_origin


def _launch_vm_instance(
    instance_name: str,
    shared_dir: Path,
    cloud_init_config: str,
    image_origin: str,
) -> None:
    """Launch the Multipass VM instance."""
    try:
        # Get the number of CPUs available
        cpu_count = str(os.cpu_count() or 2)  # Default to 2 if unable to determine

        multipass_cmd = [
            "multipass",
            "launch",
            f"-c{cpu_count}",
            "-m4GB",
            "-d10GB",
            "--mount",
            f"{shared_dir}:/shared",
            "-n",
            instance_name,
            "--cloud-init",
            "-",  # Use stdin for cloud-init
            image_origin,
        ]

        p = subprocess.Popen(
            multipass_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stdout, stderr = p.communicate(input=cloud_init_config.encode("utf-8"))

        if p.returncode != 0:
            error_details = stderr.decode().strip() if stderr else "No error details available"
            stdout_details = stdout.decode().strip() if stdout else ""

            error_msg = f"Error launching multipass instance (return code {p.returncode})"
            if error_details:
                error_msg += f"\nMultipass error: {error_details}"
            if stdout_details:
                error_msg += f"\nMultipass stdout: {stdout_details}"

            raise RuntimeError(error_msg)

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error launching multipass instance: {e}")


async def create(ctx: typer.Context, cluster: Cluster) -> typer.Exit:
    """Create a singlenode slurm cluster using multipass.

    Args:
        ctx: Typer context containing CLI configuration
        cluster: Cluster object with configuration and client credentials

    Raises:
        typer.Exit: If deployment fails due to missing or invalid cluster data
    """
    console = ctx.obj.console
    verbose = ctx.obj.verbose
    settings = ctx.obj.settings

    org_id = ctx.obj.persona.identity_data.org_id

    check_multipass_available()

    client_secret = cluster.client_secret
    sssd_binder_password = cluster.sssd_binder_password

    if sssd_binder_password is None:
        console.print(
            "[bold red]Error:[/bold red] Cluster is missing SSSD binder password. Please debug"
        )
        return typer.Exit(code=1)

    if client_secret is None:
        console.print("[bold red]Error:[/bold red] Cluster is missing client secret. Please debug")
        return typer.Exit(code=1)

    vantage_cluster_ctx = VantageClusterContext(
        cluster_name=cluster.name,
        client_id=cluster.client_id,
        client_secret=client_secret,
        base_api_url=settings.get_apis_url(),
        oidc_base_url=settings.get_auth_url(),
        oidc_domain=settings.oidc_domain,
        tunnel_api_url=settings.get_tunnel_url(),
        jupyterhub_token=cluster.creation_parameters["jupyterhub_token"],
        sssd_binder_password=sssd_binder_password,
        ldap_url=settings.get_ldap_url(),
        org_id=org_id,
    )

    cloud = cloud_sdk.get(CLOUD_LOCALHOST)
    if cloud is None:
        logger.debug(
            f"[bold red]Error:[/bold red] Cloud '{CLOUD_LOCALHOST}' not found. Please debug"
        )
        raise typer.Exit(code=1)

    deployment = create_deployment_with_init_status(
        app_name=APP_NAME,
        cluster=cluster,
        vantage_cluster_ctx=vantage_cluster_ctx,
        verbose=verbose,
        cloud=cloud,
        substrate=SUBSTRATE,
    )

    shared_dir = _prepare_shared_directory(verbose, console)
    cloud_init_config, image_origin = _generate_cloud_init_configuration(vantage_cluster_ctx)

    try:
        _launch_vm_instance(deployment.name, shared_dir, cloud_init_config, image_origin)
    except Exception as e:
        deployment.status = "error"
        deployment.write()
        ctx.obj.console.print(f"[bold red]Error:[/bold red] Deployment failed: {e}")
        return typer.Exit(code=1)

    deployment.status = "active"
    deployment.write()

    ctx.obj.console.print(success_create_message(deployment=deployment))
    return typer.Exit(0)


# Command functions that the deployment system will discover
@handle_abort
@attach_settings
async def create_command(
    ctx: typer.Context,
    cluster_name: Annotated[
        str,
        typer.Argument(help="Name of the cluster to create"),
    ],
    dev_run: Annotated[
        bool, typer.Option("--dev-run", help="Use dummy cluster data for local development")
    ] = False,
) -> None | typer.Exit:
    """Create a Vantage Multipass Singlenode SLURM cluster."""
    deploy_to_cluster: Optional[Cluster] = generate_dev_cluster_data(cluster_name)

    if not dev_run:
        from vantage_cli.sdk.cluster.crud import cluster_sdk

        if (cluster := await cluster_sdk.get_cluster_by_name(ctx, cluster_name)) is not None:
            deploy_to_cluster = cluster
        else:
            raise typer.Exit(code=1)
    else:
        raise typer.Exit(code=1)

    await create(ctx=ctx, cluster=deploy_to_cluster)


async def remove(ctx: typer.Context, deployment: Deployment) -> None:
    """Remove a Multipass SLURM deployment by deleting the instance.

    Args:
        ctx: The typer context object for console access.
        deployment: The deployment object to remove

    Raises:
        Exception: If removal fails (non-critical, logged and continued)
    """
    await _remove_deployment(deployment=deployment)


@handle_abort
@attach_settings
async def remove_command(
    ctx: typer.Context,
    deployment_id: Annotated[
        str,
        typer.Argument(help="ID of the deployment to remove"),
    ],
) -> None:
    """Remove a Vantage Multipass Singlenode SLURM cluster."""
    deployment = await deployment_sdk.get_deployment(ctx, deployment_id)
    if deployment is not None:
        await remove(ctx=ctx, deployment=deployment)
        await deployment_sdk.delete(deployment.id)
        ctx.obj.console.print(
            f"[green]✓[/green] Deployment '{deployment.name}' removed successfully"
        )
        return

    ctx.obj.console.print(f"[bold red]Error:[/bold red] Deployment '{deployment_id}' not found.")
    return


async def _remove_deployment(deployment: Deployment) -> None:
    """Remove a Multipass SLURM deployment.

    Args:
        deployment: Deployment object to remove

    Raises:
        Exception: If removal fails (non-critical, logged and continued)
    """
    instance_name = deployment.name

    multipass = which("multipass")
    if multipass is None:
        raise RuntimeError("Multipass not found in PATH")
    try:
        # Delete the instance with purge flag (-p) to completely remove it
        result = subprocess.run(
            ["multipass", "delete", instance_name, "-p"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            deployment.status = "error"
            deployment.write()
            raise RuntimeError(f"Failed to delete multipass instance: {result.stderr.strip()}")

    except Exception as e:
        logger.warning(f"Multipass cleanup failed: {e}")
        raise
