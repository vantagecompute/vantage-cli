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
from rich.panel import Panel
from typing_extensions import Annotated

from vantage_cli.apps.common import (
    generate_dev_cluster_data,
    require_client_secret,
    validate_client_credentials,
    validate_cluster_data,
)
from vantage_cli.apps.templates import CloudInitTemplate, DeploymentContext
from vantage_cli.config import attach_settings
from vantage_cli.constants import (
    ERROR_MULTIPASS_NOT_FOUND,
    MULTIPASS_CLOUD_IMAGE_DEST,
    MULTIPASS_CLOUD_IMAGE_LOCAL,
    MULTIPASS_CLOUD_IMAGE_URL,
)

# Note: Cloud-init generation now handled by centralized template engine
# See vantage_cli/apps/templates.py for CloudInitTemplate and DeploymentContext


async def deploy(ctx: typer.Context, cluster_data: Optional[Dict[str, Any]] = None) -> None:
    """Deploy a single-node SLURM cluster using Multipass.

    Args:
        ctx: Typer context containing settings and configuration
        cluster_data: Dictionary containing cluster configuration including client credentials

    Raises:
        typer.Exit: If deployment fails due to missing dependencies or invalid configuration
    """
    console = Console()
    console.print(Panel("Multipass Singlenode Application"))
    console.print("Deploying multipass singlenode application...")

    multipass = which("multipass")  # Ensure multipass is installed
    if not multipass:
        console.print(ERROR_MULTIPASS_NOT_FOUND)
        console.print(f"{os.environ.get('PATH')}")  # Print the PATH environment variable
        raise typer.Exit(code=1)

        # Validate cluster data and extract credentials
    cluster_data = validate_cluster_data(cluster_data, console)
    client_id, _ = validate_client_credentials(cluster_data, console)

    # Extract cluster name from cluster data
    cluster_name = cluster_data.get("name", "unknown-cluster")

    # Get client secret - check if it's already in cluster_data (dev mode) or fetch it
    client_secret = cluster_data.get("clientSecret")
    if not client_secret:
        # Get client secret from API (import locally to avoid circular import)
        from vantage_cli.commands.cluster import utils as cluster_utils

        client_secret = await cluster_utils.get_cluster_client_secret(ctx=ctx, client_id=client_id)

    client_secret = require_client_secret(client_secret, console)

    logger.debug("Client secret obtained (or placeholder used).")

    # Use jupyterhub_token from cluster data if available, otherwise generate a default
    jupyterhub_token = None
    if cluster_data and "creationParameters" in cluster_data:
        if jupyterhub_token_data := cluster_data["creationParameters"].get("jupyterhub_token"):
            jupyterhub_token = jupyterhub_token_data
    if not jupyterhub_token:
        jupyterhub_token = "default-token-for-testing"

    logger.debug(f"Using JupyterHub token: {jupyterhub_token[:10]}...")

    # Create deployment context for template engine
    deployment_context = DeploymentContext(
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
    console.print(f"Launching: {instance_name}")

    shared_dir = Path.home() / "multipass-singlenode" / "shared"
    shared_dir.mkdir(parents=True, exist_ok=True)
    shared_dir.chmod(0o755)  # Fixed: use Path.chmod instead of shutil.chmod

    # Use a standard Ubuntu image for now since the custom Vantage image may not be available
    image_origin = MULTIPASS_CLOUD_IMAGE_URL
    if MULTIPASS_CLOUD_IMAGE_LOCAL.exists():
        image_origin = f"file://{MULTIPASS_CLOUD_IMAGE_LOCAL}"
    elif MULTIPASS_CLOUD_IMAGE_DEST.exists():
        image_origin = f"file://{MULTIPASS_CLOUD_IMAGE_DEST}"
    # Note: Fallback to standard Ubuntu image if custom image not available

    try:
        # Get the number of CPUs available
        cpu_count = str(os.cpu_count() or 2)  # Default to 2 if unable to determine

        p = subprocess.Popen(
            [
                "multipass",
                "launch",
                "--verbose",
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
            ],
            stdin=subprocess.PIPE,
        )
        # Generate cloud-init configuration using template engine
        cloud_init_template = CloudInitTemplate()
        cloud_init_config = cloud_init_template.generate_multipass_config(deployment_context)
        p.communicate(input=cloud_init_config.encode("utf-8"))

        if p.returncode == 0:
            console.print(f"[green]Successfully launched instance: {instance_name}[/green]")
            console.print("Use 'multipass list' to see the instance status.")
            console.print(f"Use 'multipass shell {instance_name}' to access the instance shell.")
            console.print("Remember to set up your SSH keys for passwordless access if needed.")
            console.print(
                "It may take a few minutes for all services to start inside the instance."
            )
        else:
            console.print(
                f"[red]Error launching multipass instance: return code {p.returncode}[/red]"
            )
            raise typer.Exit(code=1)

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error launching multipass instance: {e}[/red]")
        raise typer.Exit(code=1)


# Typer CLI commands
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
    console = Console()
    console.print(Panel("Multipass Singlenode SLURM Application"))
    console.print("Deploying multipass singlenode slurm application...")

    cluster_data = None

    if dev_run:
        console.print(
            f"[blue]Using dev run mode with dummy cluster data for '{cluster_name}'[/blue]"
        )
        cluster_data = generate_dev_cluster_data(cluster_name)
    else:
        # Import locally to avoid circular import
        from vantage_cli.commands.cluster import utils as cluster_utils

        cluster_data = await cluster_utils.get_cluster_by_name(ctx=ctx, cluster_name=cluster_name)

        if not cluster_data:
            console.print("[red]Error: No cluster data found.[/red]")
            raise typer.Exit(code=1)

    await deploy(ctx=ctx, cluster_data=cluster_data)


async def cleanup_multipass_localhost(cluster_data: Dict[str, Any]) -> None:
    """Clean up a Multipass SLURM deployment by deleting the instance.

    Args:
        cluster_data: Dictionary containing deployment information including deployment_name

    Raises:
        Exception: If cleanup fails (non-critical, logged and continued)
    """
    console = Console()

    try:
        # Extract deployment_name from cluster_data
        deployment_name = cluster_data.get("deployment_name")
        if not deployment_name:
            # Fallback to old pattern for backward compatibility
            client_id = cluster_data.get("client_id")
            if client_id:
                deployment_name = f"vantage-multipass-singlenode-{client_id.split('-')[0]}"
            else:
                console.print(
                    "[yellow]Warning: No deployment_name or client_id found in cluster_data for cleanup[/yellow]"
                )
                return

        # Use deployment_name as instance name (matches deploy function)
        instance_name = deployment_name

        console.print(f"[blue]Cleaning up Multipass instance: {instance_name}[/blue]")

        # Check if multipass is available
        multipass = which("multipass")
        if not multipass:
            console.print(
                "[yellow]Warning: multipass command not found, skipping cleanup[/yellow]"
            )
            return

        # Delete the instance with purge flag (-p) to completely remove it
        result = subprocess.run(
            ["multipass", "delete", instance_name, "-p"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            console.print(
                f"[green]Successfully deleted Multipass instance: {instance_name}[/green]"
            )
        else:
            # Instance might not exist or already deleted - not a critical error
            console.print(
                f"[yellow]Multipass delete returned code {result.returncode}: {result.stderr.strip()}[/yellow]"
            )
            console.print("[yellow]Instance may not exist or was already deleted[/yellow]")

    except subprocess.TimeoutExpired:
        console.print("[yellow]Warning: Multipass delete operation timed out[/yellow]")
    except Exception as e:
        console.print(f"[yellow]Warning: Error during Multipass cleanup: {e}[/yellow]")
        logger.warning(f"Multipass cleanup failed: {e}")
