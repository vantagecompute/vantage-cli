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
from typing import Any, Dict

import typer
from loguru import logger
from rich.console import Console
from typing_extensions import Annotated

from vantage_cli.apps.common import (
    create_deployment_with_init_status,
    generate_default_deployment_name,
    generate_dev_cluster_data,
    require_client_secret,
    update_deployment_status,
    validate_client_credentials,
    validate_cluster_data,
)
from vantage_cli.apps.slurm_multipass_localhost.utils import check_multipass_available
from vantage_cli.apps.templates import CloudInitTemplate
from vantage_cli.config import attach_settings
from vantage_cli.constants import (
    CLOUD_LOCALHOST,
    CLOUD_TYPE_VM,
    MULTIPASS_CLOUD_IMAGE_DEST,
    MULTIPASS_CLOUD_IMAGE_LOCAL,
    MULTIPASS_CLOUD_IMAGE_URL,
)
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import DeploymentStep, deployment_progress_panel
from vantage_cli.schemas import VantageClusterContext

# Note: Cloud-init generation now handled by centralized template engine
# See vantage_cli/apps/templates.py for CloudInitTemplate and VantageClusterContext


def _validate_and_extract_credentials(
    cluster_data: Dict[str, Any], console: Console
) -> tuple[str, str | None]:
    """Validate cluster data and extract client credentials.

    Returns:
        Tuple of (client_id, client_secret)
    """
    cluster_data = validate_cluster_data(cluster_data, console)
    client_id, client_secret = validate_client_credentials(cluster_data, console)
    return client_id, client_secret


async def _get_client_secret_if_needed(
    ctx: typer.Context, client_id: str, cluster_data: Dict[str, Any], console: Console
) -> str:
    """Get client secret from API if not already in cluster data."""
    client_secret = cluster_data.get("clientSecret")
    if not client_secret:
        try:
            from vantage_cli.commands.cluster import utils as cluster_utils

            client_secret = await cluster_utils.get_cluster_client_secret(
                ctx=ctx, client_id=client_id
            )
        except Exception as e:
            console.print(f"[red]Failed to get client secret: {e}[/red]")
            raise
    return require_client_secret(client_secret, console)


def _create_deployment_with_id(
    app_name: str, cluster_name: str, cluster_data: Dict[str, Any], console: Console, verbose: bool
) -> str:
    """Create deployment with initial status and return deployment ID."""
    deployment_id = generate_default_deployment_name(app_name, cluster_name)
    create_deployment_with_init_status(
        deployment_id=deployment_id,
        app_name=app_name,
        cluster_name=cluster_name,
        cluster_data=cluster_data,
        console=console,
        verbose=verbose,
        cloud=CLOUD_LOCALHOST,
        cloud_type=CLOUD_TYPE_VM,
    )
    return deployment_id


def _get_jupyterhub_token(cluster_data: Dict[str, Any], verbose: bool) -> str:
    """Get or generate JupyterHub token from cluster data."""
    jupyterhub_token = None
    if cluster_data and "creationParameters" in cluster_data:
        if jupyterhub_token_data := cluster_data["creationParameters"].get("jupyterhub_token"):
            jupyterhub_token = jupyterhub_token_data
    if not jupyterhub_token:
        jupyterhub_token = "default-token-for-testing"

    if verbose:
        logger.debug(f"Using JupyterHub token: {jupyterhub_token[:10]}...")

    return jupyterhub_token


def _create_final_success_message(client_id: str, instance_name: str, deployment_id: str) -> str:
    """Create the final success message for deployment completion."""
    return f"""🎉 [bold green]SLURM Multipass deployment completed successfully![/bold green]

Access your cluster in the Vantage UI: [cyan]https://app.vantagecompute.ai/compute/clusters/{client_id}[/cyan]

[bold]Deployment Summary:[/bold]
• VM instance name: [cyan]{instance_name}[/cyan]
• Shared directory: [cyan]~/multipass-singlenode/shared[/cyan]
• Cloud image: [cyan]Ubuntu 24.04 LTS[/cyan]
• Deployment ID: [cyan]{deployment_id}[/cyan]

[bold]Connect to SLURM Cluster:[/bold]
• Access VM shell: [cyan]multipass shell {instance_name}[/cyan]
• SSH into VM: [cyan]multipass exec {instance_name} -- bash[/cyan]
• Get VM IP address: [cyan]multipass info {instance_name} | grep IPv4[/cyan]
• SSH with external access: [cyan]ssh ubuntu@$(multipass info {instance_name} --format json | jq -r '.info."{instance_name}".ipv4[0]')[/cyan]

[bold]SLURM Job Management:[/bold]
• Check SLURM status: [cyan]multipass exec {instance_name} -- systemctl status slurmd[/cyan]
• Submit test job: [cyan]multipass exec {instance_name} -- sinfo[/cyan]
• Check job queue: [cyan]multipass exec {instance_name} -- squeue[/cyan]
• Node information: [cyan]multipass exec {instance_name} -- scontrol show nodes[/cyan]
• Run interactive job: [cyan]multipass exec {instance_name} -- srun --pty bash[/cyan]

[bold]File Management:[/bold]
• Copy files to VM: [cyan]multipass transfer <local-file> {instance_name}:<vm-path>[/cyan]
• Copy files from VM: [cyan]multipass transfer {instance_name}:<vm-path> <local-file>[/cyan]
• Mount directories: [cyan]multipass mount <local-path> {instance_name}:<vm-path>[/cyan]
• Unmount directories: [cyan]multipass umount {instance_name}:<vm-path>[/cyan]

[bold]VM Management:[/bold]
• Check VM status: [cyan]multipass list[/cyan]
• View VM details: [cyan]multipass info {instance_name}[/cyan]
• VM resource usage: [cyan]multipass info {instance_name} --format json[/cyan]
• Stop VM: [cyan]multipass stop {instance_name}[/cyan]
• Start VM: [cyan]multipass start {instance_name}[/cyan]
• Restart VM: [cyan]multipass restart {instance_name}[/cyan]

[bold]Monitoring & Logs:[/bold]
• Check cloud-init status: [cyan]multipass exec {instance_name} -- cloud-init status[/cyan]
• View cloud-init logs: [cyan]multipass exec {instance_name} -- cat /var/log/cloud-init-output.log[/cyan]
• System logs: [cyan]multipass exec {instance_name} -- journalctl -u slurmd[/cyan]

[bold]Other Commands:[/bold]
• Check cluster status: [cyan]vantage deployment slurm-multipass-localhost status[/cyan]
• Remove deployment: [cyan]vantage deployment slurm-multipass-localhost remove[/cyan]

[yellow]Note:[/yellow] It may take a few minutes for all services to start inside the VM. Check cloud-init status for progress."""


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


def _show_deployment_error(console: Console, cluster_name: str, error: Exception) -> None:
    """Show deployment error message and troubleshooting steps."""
    console.print()
    console.print("❌ [bold red]SLURM Multipass deployment failed![/bold red]")
    console.print(f"[red]Error: {str(error)}[/red]")
    console.print()
    console.print("[bold]Troubleshooting Steps:[/bold]")
    console.print("• Check Multipass status: [cyan]multipass version[/cyan]")
    console.print("• List existing VMs: [cyan]multipass list[/cyan]")
    console.print("• Check VM logs: [cyan]multipass info <vm-name> --format yaml[/cyan]")
    console.print("• Delete failed VM: [cyan]multipass delete <vm-name> --purge[/cyan]")
    console.print(
        f"• Retry with verbose output: [cyan]vantage deployment slurm-multipass-localhost deploy {cluster_name} --verbose[/cyan]"
    )
    console.print(
        "• Remove failed deployment: [cyan]vantage deployment slurm-multipass-localhost remove[/cyan]"
    )
    console.print()


async def deploy(ctx: typer.Context, cluster_data: Dict[str, Any], verbose: bool = False) -> None:
    """Deploy a single-node SLURM cluster using Multipass.

    Args:
        ctx: Typer context containing settings and configuration
        cluster_data: Dictionary containing cluster configuration including client credentials
        verbose: Whether to show verbose output

    Raises:
        typer.Exit: If deployment fails due to missing dependencies or invalid configuration
    """
    console = ctx.obj.console

    # Validate cluster data and extract credentials
    client_id, client_secret = _validate_and_extract_credentials(cluster_data, console)

    # Get client secret from API if not in cluster data
    if not client_secret:
        client_secret = await _get_client_secret_if_needed(ctx, client_id, cluster_data, console)

    # Extract cluster name from cluster data
    cluster_name = cluster_data.get("name", "unknown-cluster")

    # Generate deployment ID and create deployment with init status
    app_name = "slurm-multipass-localhost"
    deployment_id = _create_deployment_with_id(
        app_name, cluster_name, cluster_data, console, verbose
    )

    if verbose:
        logger.debug("Client secret obtained (or placeholder used).")

    # Get JupyterHub token from cluster data or use default
    jupyterhub_token = _get_jupyterhub_token(cluster_data, verbose)

    # Create deployment context for template engine
    deployment_context = VantageClusterContext(
        cluster_name=cluster_name,
        client_id=client_id,
        client_secret=client_secret,
        oidc_domain=ctx.obj.settings.oidc_domain,
        oidc_base_url=ctx.obj.settings.oidc_base_url,
        base_api_url=ctx.obj.settings.api_base_url,
        tunnel_api_url=ctx.obj.settings.tunnel_api_url,
        jupyterhub_token=jupyterhub_token,
    )

    # Use deployment_name as instance name for easier cleanup
    deployment_name = cluster_data.get(
        "deployment_name", f"vantage-multipass-singlenode-{client_id.split('-')[0]}"
    )
    instance_name = deployment_name

    # Define deployment steps
    steps = [
        DeploymentStep("Check Multipass availability"),
        DeploymentStep("Prepare shared directory"),
        DeploymentStep("Generate cloud-init configuration"),
        DeploymentStep("Launch VM instance"),
        DeploymentStep("Finalize deployment"),
    ]

    deployment_success = False

    # Create final success message for the panel
    final_success_message = _create_final_success_message(client_id, instance_name, deployment_id)

    try:
        with deployment_progress_panel(
            steps=steps,
            console=console,
            verbose=verbose,
            title="Deploying SLURM Multipass",
            panel_title="🚀 SLURM Multipass Deployment Progress",
            final_message=final_success_message,
        ) as advance_step:
            advance_step("Check Multipass availability", "starting")
            # Ensure multipass is installed
            check_multipass_available()
            advance_step("Check Multipass availability", "completed")

            advance_step("Prepare shared directory", "starting")
            shared_dir = _prepare_shared_directory(verbose, console)
            advance_step("Prepare shared directory", "completed")

            advance_step("Generate cloud-init configuration", "starting")
            cloud_init_config, image_origin = _generate_cloud_init_configuration(
                deployment_context, verbose, console
            )
            advance_step("Generate cloud-init configuration", "completed")

            advance_step("Launch VM instance", "starting")
            _launch_vm_instance(
                instance_name, shared_dir, cloud_init_config, image_origin, verbose, console
            )
            advance_step("Launch VM instance", "completed")

            advance_step("Finalize deployment", "starting")

            # Small pause to show the "starting" state
            import time

            time.sleep(1)

            advance_step("Finalize deployment", "completed", show_final=True)

            # Extended pause to allow users to read the final message in the panel
            time.sleep(10)  # 10 seconds to read the success message

            deployment_success = True

        # Update deployment status after the Live panel is done
        if deployment_success:
            update_deployment_status(deployment_id, "active", console, verbose=verbose)
        else:
            update_deployment_status(deployment_id, "failed", console, verbose=verbose)
            raise typer.Exit(1)

    except Exception as e:
        # Update deployment status to failed on error
        update_deployment_status(deployment_id, "failed", console, verbose=verbose)

        # Show error message and troubleshooting steps
        _show_deployment_error(console, cluster_name, e)

        raise typer.Exit(1)


# Typer CLI commands
@handle_abort
@attach_settings
async def deploy_command(
    ctx: typer.Context,
    cluster_name: Annotated[
        str,
        typer.Argument(help="Name of the cluster to deploy"),
    ],
    dev_run: Annotated[
        bool, typer.Option("--dev-run", help="Use dummy cluster data for local development")
    ] = False,
) -> None:
    """Deploy a Vantage Multipass Singlenode SLURM cluster."""
    # Check for Multipass early before doing any other work
    check_multipass_available()

    cluster_data = generate_dev_cluster_data(cluster_name)
    if not dev_run:
        from vantage_cli.commands.cluster import utils as cluster_utils

        cluster_data = await cluster_utils.get_cluster_by_name(ctx=ctx, cluster_name=cluster_name)
        if cluster_data is None:
            raise ValueError(f"Cluster '{cluster_name}' not found")

    await deploy(ctx=ctx, cluster_data=cluster_data)


async def cleanup_multipass_localhost(ctx: typer.Context, cluster_data: Dict[str, Any]) -> None:
    """Clean up a Multipass SLURM deployment by deleting the instance.

    Args:
        ctx: The typer context object for console access.
        cluster_data: Dictionary containing deployment information including deployment_name

    Raises:
        Exception: If cleanup fails (non-critical, logged and continued)
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

    # Use deployment_name as instance name (matches deploy function)
    instance_name = deployment_name

    # Get deployment ID for final message
    deployment_id = cluster_data.get("deployment_id", "N/A")

    # Define cleanup steps
    steps = [
        DeploymentStep("Check Multipass availability"),
        DeploymentStep("Delete Multipass instance"),
        DeploymentStep("Cleanup complete"),
    ]

    # Create final success message for the panel
    final_success_message = f"""✅ [bold green]SLURM Multipass cleanup completed successfully![/bold green]

[bold]Cleanup Summary:[/bold]
• Deployment ID: [cyan]{deployment_id}[/cyan]
• Instance '{instance_name}' deleted
• Storage purged
• Resources freed

[bold]Next Steps:[/bold]
• List instances: [cyan]multipass list[/cyan]
• Deploy new cluster: [cyan]vantage deployment slurm-multipass-localhost deploy <cluster-name>[/cyan]"""

    try:
        with deployment_progress_panel(
            steps=steps,
            console=console,
            verbose=False,  # Always use panel mode for clean display
            title="Cleaning up SLURM Multipass",
            panel_title="🧹 SLURM Multipass Cleanup Progress",
            final_message=final_success_message,
        ) as advance_step:
            advance_step("Check Multipass availability", "starting")

            # Check if multipass is available
            multipass = which("multipass")
            if not multipass:
                advance_step("Check Multipass availability", "warning")
                console.print(
                    "[yellow]Warning: multipass command not found, skipping cleanup[/yellow]"
                )
                return

            advance_step("Check Multipass availability", "completed")

            advance_step("Delete Multipass instance", "starting")

            try:
                # Delete the instance with purge flag (-p) to completely remove it
                result = subprocess.run(
                    ["multipass", "delete", instance_name, "-p"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode == 0:
                    advance_step("Delete Multipass instance", "completed")
                else:
                    # Instance might not exist or already deleted - not a critical error
                    advance_step("Delete Multipass instance", "warning")
                    logger.warning(
                        f"Multipass delete returned code {result.returncode}: {result.stderr.strip()}"
                    )

            except subprocess.TimeoutExpired:
                advance_step("Delete Multipass instance", "warning")
                logger.warning("Multipass delete operation timed out")
            except Exception as e:
                advance_step("Delete Multipass instance", "warning")
                logger.warning(f"Error during Multipass cleanup: {e}")

            advance_step("Cleanup complete", "starting")

            # Small pause to show the "starting" state
            import time

            time.sleep(1)

            advance_step("Cleanup complete", "completed", show_final=True)

            # Extended pause to allow users to read the final message in the panel
            time.sleep(8)  # 8 seconds to read the success message

    except Exception as e:
        logger.warning(f"Multipass cleanup failed: {e}")
        raise
