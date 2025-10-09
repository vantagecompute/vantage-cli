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

import os
import subprocess
from pathlib import Path
from shutil import which
from typing import Any, Dict, Optional

import typer
from loguru import logger
from rich.console import Console
from typing_extensions import Annotated

from vantage_cli.apps.common import (
    create_deployment_with_init_status,
    generate_default_deployment_name,
    generate_dev_cluster_data,
    get_jupyterhub_token,
    get_sssd_binder_password,
    update_deployment_status,
    validate_client_credentials,
)
from vantage_cli.apps.constants import DEV_CLIENT_SECRET, DEV_SSSD_BINDER_PASSWORD, DEV_JUPYTERHUB_TOKEN
from vantage_cli.config import attach_settings
from vantage_cli.constants import (
    CLOUD_LOCALHOST,
    CLOUD_TYPE_VM,
    MULTIPASS_CLOUD_IMAGE_DEST,
    MULTIPASS_CLOUD_IMAGE_LOCAL,
    MULTIPASS_CLOUD_IMAGE_URL,
)
from vantage_cli.exceptions import handle_abort
from vantage_cli.sdk.cluster.schema import Cluster, VantageClusterContext

from .constants import APP_NAME
from .templates import CloudInitTemplate
from .utils import check_multipass_available, is_ready
from .render import show_deployment_error
from vantage_cli.render import RenderStepOutput



def _prepare_shared_directory(verbose: bool, console: Console) -> Path:
    """Prepare shared directory for VM mounting."""
    shared_dir = Path.home() / "multipass-singlenode" / "shared"
    shared_dir.mkdir(parents=True, exist_ok=True)
    shared_dir.chmod(0o755)  # Fixed: use Path.chmod instead of shutil.chmod

    if verbose:
        console.print(f"Prepared shared directory: {shared_dir}")

    return shared_dir


def _generate_cloud_init_configuration(
    deployment_context: VantageClusterContext, verbose: bool, console: Console
) -> tuple[str, str]:
    """Generate cloud-init configuration and determine image origin.

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
    cloud_init_config = cloud_init_template.generate_multipass_config(deployment_context)

    if verbose:
        console.print(f"Using image: {image_origin}")
        console.print("Generated cloud-init configuration")

    return cloud_init_config, image_origin


def _launch_vm_instance(
    instance_name: str,
    shared_dir: Path,
    cloud_init_config: str,
    image_origin: str,
    verbose: bool,
    console: Console,
) -> None:
    """Launch the Multipass VM instance."""
    try:
        # Get the number of CPUs available
        cpu_count = str(os.cpu_count() or 2)  # Default to 2 if unable to determine

        if verbose:
            console.print(f"Launching instance: {instance_name}")
            console.print(f"CPU count: {cpu_count}, Memory: 4GB, Disk: 10GB")

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

        # Add verbose flag if requested
        if verbose:
            multipass_cmd.insert(2, "--verbose")

        p = subprocess.Popen(
            multipass_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stdout, stderr = p.communicate(input=cloud_init_config.encode("utf-8"))

        if p.returncode == 0:
            if verbose:
                console.print(f"Successfully launched instance: {instance_name}")
                if stdout:
                    console.print(f"Stdout: {stdout.decode().strip()}")
        else:
            error_details = stderr.decode().strip() if stderr else "No error details available"
            stdout_details = stdout.decode().strip() if stdout else ""

            error_msg = f"Error launching multipass instance (return code {p.returncode})"
            if error_details:
                error_msg += f"\nMultipass error: {error_details}"
            if stdout_details and verbose:
                error_msg += f"\nMultipass stdout: {stdout_details}"

            raise RuntimeError(error_msg)

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error launching multipass instance: {e}")


async def _create_deployment(ctx: typer.Context, cluster_obj: Cluster) -> None:
    """Internal function to create a single-node SLURM cluster using Multipass.

    Args:
        ctx: Typer context containing settings and configuration
        cluster_obj: Cluster object containing cluster configuration including client credentials

    Raises:
        typer.Exit: If deployment fails due to missing dependencies or invalid configuration
    """
    console = ctx.obj.console
    verbose = ctx.obj.verbose
    json_output = ctx.obj.json_output
    command_start_time = ctx.obj.command_start_time

    cluster_name = cluster_obj.name

    client_id, client_secret = validate_client_credentials(cluster_obj, console)
    
    # Import locally to avoid circular import
    from vantage_cli.commands.cluster.utils import get_cluster_client_secret
    client_secret = await get_cluster_client_secret(ctx=ctx, client_id=client_id)

    deployment_id = generate_default_deployment_name(APP_NAME, cluster_name)
    deployment_name = f"multipass-singlenode-{client_id.split('-')[0]}"

    org_id = ctx.obj.persona.identity_data.org_id
    jupyterhub_token = get_jupyterhub_token(cluster_obj)
    sssd_binder_password = get_sssd_binder_password(cluster_obj)

    deployment_context = VantageClusterContext(
        cluster_name=cluster_name,
        client_id=client_id,
        client_secret=client_secret or DEV_CLIENT_SECRET,
        oidc_domain=ctx.obj.settings.oidc_domain,
        oidc_base_url=ctx.obj.settings.get_auth_url(),
        base_api_url=ctx.obj.settings.get_apis_url(),
        tunnel_api_url=ctx.obj.settings.get_tunnel_url(),
        ldap_url=ctx.obj.settings.get_ldap_url(),
        sssd_binder_password=sssd_binder_password or DEV_SSSD_BINDER_PASSWORD,
        org_id=org_id,
        jupyterhub_token=jupyterhub_token or DEV_JUPYTERHUB_TOKEN,
    )

    instance_name = deployment_name

    create_deployment_with_init_status(
        deployment_id=deployment_id,
        app_name=APP_NAME,
        cluster_name=cluster_name,
        cluster=cluster_obj,
        console=console,
        deployment_name=deployment_name,
        verbose=verbose,
        cloud=CLOUD_LOCALHOST,
        cloud_type=CLOUD_TYPE_VM,
        k8s_namespaces=[],
    )

    renderer = RenderStepOutput(
        console=console,
        operation_name=f"Creating SLURM Multipass deployment '{cluster_name}'",
        step_names=[
            "Check Multipass availability",
            "Prepare shared directory",
            "Generate cloud-init configuration",
            "Launch VM instance",
            "Update deployment status",
        ],
        verbose=verbose,
        command_start_time=command_start_time,
        json_output=json_output,
    )

    try:
        with renderer:
            renderer.start_step("Check Multipass availability")
            # Ensure multipass is installed
            check_multipass_available()
            renderer.complete_step("Check Multipass availability")

            renderer.start_step("Prepare shared directory")
            shared_dir = _prepare_shared_directory(verbose, console)
            renderer.complete_step("Prepare shared_directory")

            renderer.start_step("Generate cloud-init configuration")
            cloud_init_config, image_origin = _generate_cloud_init_configuration(
                deployment_context, verbose, console
            )
            renderer.complete_step("Generate cloud-init configuration")

            renderer.start_step("Launch VM instance")
            _launch_vm_instance(
                instance_name, shared_dir, cloud_init_config, image_origin, verbose, console
            )
            renderer.complete_step("Launch VM instance")

            renderer.start_step("Update deployment status")
            update_deployment_status(deployment_id, "active", console, verbose=verbose)
            renderer.complete_step("Update deployment status")

            if json_output:
                renderer.json_bypass({
                    "deployment_id": deployment_id,
                    "cluster_name": cluster_name,
                    "instance_name": instance_name,
                    "client_id": client_id,
                    "status": "active"
                })

    except Exception as e:
        # Update deployment status to failed on error
        update_deployment_status(deployment_id, "failed", console, verbose=verbose)

        # Log the exception for debugging
        logger.error(f"Deployment failed with exception: {type(e).__name__}: {e}")
        if verbose:
            logger.exception("Full traceback:")

        # Show error message and troubleshooting steps if not JSON mode
        if not json_output:
            show_deployment_error(console, cluster_name, e)

        raise typer.Exit(1)


# Core implementation functions
async def create(ctx: typer.Context, cluster_obj: Cluster) -> None:
    """Create a single-node SLURM cluster using Multipass.

    Args:
        ctx: Typer context containing settings and configuration
        cluster_obj: Cluster object containing cluster configuration including client credentials

    Raises:
        typer.Exit: If deployment fails due to missing dependencies or invalid configuration
    """
    await _create_deployment(ctx=ctx, cluster_obj=cluster_obj)


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
) -> None:
    """Create a Vantage Multipass Singlenode SLURM cluster."""
    check_multipass_available()

    # Import cluster_utils locally to avoid circular import
    from vantage_cli.commands.cluster import utils as cluster_utils

    if dev_run:
        cluster_obj = generate_dev_cluster_data(cluster_name)
    else:
        cluster_obj = await cluster_utils.get_cluster_by_name(ctx=ctx, cluster_name=cluster_name)
        if cluster_obj is None:
            raise ValueError(f"Cluster '{cluster_name}' not found")
    
    # Pass Cluster object directly to create function
    await create(ctx=ctx, cluster_obj=cluster_obj)


async def remove(ctx: typer.Context, cluster_data: Dict[str, Any]) -> None:
    """Remove a Multipass SLURM deployment by deleting the instance.

    Args:
        ctx: The typer context object for console access.
        cluster_data: Dictionary containing deployment information including deployment_name

    Raises:
        Exception: If removal fails (non-critical, logged and continued)
    """
    await _remove_deployment(ctx=ctx, cluster_data=cluster_data)


@handle_abort
@attach_settings
async def remove_command(
    ctx: typer.Context,
    deployment_name: Annotated[
        str,
        typer.Argument(help="Name of the deployment to remove"),
    ],
) -> None:
    """Remove a Vantage Multipass Singlenode SLURM cluster."""
    # Load deployment data
    cluster_data = {"deployment_name": deployment_name}
    await remove(ctx=ctx, cluster_data=cluster_data)


async def _remove_deployment(ctx: typer.Context, cluster_data: Dict[str, Any]) -> None:
    """Internal function to remove a Multipass SLURM deployment.

    Args:
        ctx: The typer context object for console access.
        cluster_data: Dictionary containing deployment information including deployment_name

    Raises:
        Exception: If removal fails (non-critical, logged and continued)
    """
    console = ctx.obj.console
    verbose = getattr(ctx.obj, "verbose", False)

    # Extract deployment_name from cluster_data
    deployment_name = cluster_data.get("deployment_name")
    if not deployment_name:
        # Fallback to old pattern for backward compatibility
        client_id = cluster_data.get("client_id")
        if client_id:
            deployment_name = f"vantage-multipass-singlenode-{client_id.split('-')[0]}"
        else:
            # Only show this warning in verbose mode or if it's not a dev deployment
            if verbose or not cluster_data.get("deployment_id", "").startswith(
                "slurm-multipass-localhost-dev"
            ):
                console.print(
                    "[yellow]Warning: No deployment_name or client_id found in cluster_data for cleanup[/yellow]"
                )
            return

    # Use deployment_name as instance name (matches create function)
    instance_name = deployment_name

    # Get deployment ID for final message
    deployment_id = cluster_data.get("deployment_id", "N/A")

    # Get JSON output flag
    json_output = getattr(ctx.obj, "json_output", False)
    command_start_time = getattr(ctx.obj, "command_start_time", None)

    # Create RenderStepOutput for clean progress tracking
    renderer = RenderStepOutput(
        console=console,
        operation_name=f"Removing SLURM Multipass deployment '{instance_name}'",
        step_names=[
            "Check Multipass availability",
            "Delete Multipass instance",
        ],
        verbose=verbose,
        command_start_time=command_start_time,
        json_output=json_output,
    )

    try:
        with renderer:
            renderer.start_step("Check Multipass availability")

            # Check if multipass is available
            multipass = which("multipass")
            if not multipass:
                logger.warning("multipass command not found, skipping cleanup")
                renderer.complete_step("Check Multipass availability")
                if json_output:
                    renderer.json_bypass({
                        "deployment_id": deployment_id,
                        "instance_name": instance_name,
                        "status": "skipped",
                        "message": "multipass command not found"
                    })
                return

            renderer.complete_step("Check Multipass availability")

            renderer.start_step("Delete Multipass instance")

            try:
                # Delete the instance with purge flag (-p) to completely remove it
                result = subprocess.run(
                    ["multipass", "delete", instance_name, "-p"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode == 0:
                    renderer.complete_step("Delete Multipass instance")
                    if json_output:
                        renderer.json_bypass({
                            "deployment_id": deployment_id,
                            "instance_name": instance_name,
                            "status": "deleted"
                        })
                else:
                    # Instance might not exist or already deleted - not a critical error
                    logger.warning(
                        f"Multipass delete returned code {result.returncode}: {result.stderr.strip()}"
                    )
                    renderer.complete_step("Delete Multipass instance")
                    if json_output:
                        renderer.json_bypass({
                            "deployment_id": deployment_id,
                            "instance_name": instance_name,
                            "status": "warning",
                            "message": result.stderr.strip()
                        })

            except subprocess.TimeoutExpired:
                logger.warning("Multipass delete operation timed out")
                renderer.complete_step("Delete Multipass instance")
                if json_output:
                    renderer.json_bypass({
                        "deployment_id": deployment_id,
                        "instance_name": instance_name,
                        "status": "timeout"
                    })
            except Exception as e:
                logger.warning(f"Error during Multipass cleanup: {e}")
                renderer.complete_step("Delete Multipass instance")
                if json_output:
                    renderer.json_bypass({
                        "deployment_id": deployment_id,
                        "instance_name": instance_name,
                        "status": "error",
                        "message": str(e)
                    })

    except Exception as e:
        logger.warning(f"Multipass cleanup failed: {e}")
        raise
