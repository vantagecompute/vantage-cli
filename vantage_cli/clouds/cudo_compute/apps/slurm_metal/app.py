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
#!/usr/bin/env python3
# Copyright (c) 2025 Vantage Compute Corporation
# See LICENSE file for licensing details.
"""Cudo Compute SLURM on Metal deployment app for Vantage CLI."""

import asyncio
import copy
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

import logging

from vantage_cli.clouds.cudo_compute.slurm_metal.constants import CLOUD
from vantage_cli.sdk.cloud.crud import cloud_sdk
from vantage_cli.sdk.cloud_credential.crud import cloud_credential_sdk
from vantage_cli.sdk.cloud_credential.schema import CloudCredential
from vantage_cli.clouds.cudo_compute.sdk import CudoComputeSDK

logger = logging.getLogger(__name__)
import typer
import yaml
from typing_extensions import Annotated

from vantage_cli.clouds.common import (
    create_deployment_with_init_status,
    generate_dev_cluster_data,
)

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.sdk.admin.management.organizations import get_extra_attributes
from vantage_cli.sdk.cluster.schema import Cluster, VantageClusterContext
from vantage_cli.sdk.deployment.schema import Deployment

from vantage_cli.sdk.deployment.crud import deployment_sdk

from vantage_cli.vantage_rest_api_client import attach_vantage_rest_client

from .constants import APP_NAME, SUBSTRATE
from .render import success_create_message, success_destroy_message


async def _deploy_slurm_metal_cudo(ctx: typer.Context) -> None:
    """Deploy SLURM on metal using Cudo Compute.

    Args:
        ctx: VantageClusterContext containing deployment configuration

    Raises:
        Exception: If deployment fails
    """
    cudo_credential: Optional[CloudCredential] = None

    # Get the Cudo Compute cloud configuration
    cloud = cloud_sdk.get(CLOUD)
    if cloud is None:
        logger.debug(f"[bold red]Error:[/bold red] Cloud '{CLOUD}' not found. Please debug")
        raise typer.Exit(code=1)

    # Get the default credential for Cudo Compute
    cudo_credential = cloud_credential_sdk.get_default(cloud_name=CLOUD)
    if cudo_credential is None:
        logger.debug(f"[bold red]Error:[/bold red] No default credential found for '{CLOUD}'")
        logger.debug(f"Run: vantage cloud credential create --cloud {CLOUD}")
        raise typer.Exit(code=1)

    # Initialize Cudo Compute SDK
    cudo_sdk = CudoComputeSDK(api_key=cudo_credential.credentials_data["api_key"])
    if cudo_sdk is None:
        logger.debug("[bold red]Error:[/bold red] Failed to initialize Cudo Compute SDK")
        raise typer.Exit(code=1)
    
    logger.debug(f"Using Cudo Compute credential: {cudo_credential.name} (ID: {cudo_credential.id})")
    logger.debug(f"Using credential {cudo_credential.name} (ID: {cudo_credential.id}) for cloud: {cloud.name} (ID: {cloud.id})")
    logger.debug(f"{await cudo_sdk.whoami()}")

    # Create a project
    project = await cudo_sdk.create_project(
        name="vantage-slurm-metal-project",
        description="Project for Vantage SLURM deployment",
        tags=["vantage", "slurm", "metal"],
    )

    logger.debug(f"Created project: {project['name']} (ID: {project['id']})")

    # Create 

    await cudo_sdk.create_vm(
        name="vantage-slurm-metal",
    )


async def create(ctx: typer.Context, cluster: Cluster) -> typer.Exit:
    """Create Juju localhost Charmed HPC cluster using cluster data.

    Args:
        ctx: Typer context containing CLI configuration
        cluster_obj: Cluster object with configuration and client credentials

    Raises:
        typer.Exit: If deployment fails due to missing or invalid cluster data
    """
    verbose = ctx.obj.verbose
    settings = ctx.obj.settings
    console = ctx.obj.console

    org_id = ctx.obj.persona.identity_data.org_id

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

    deployment = create_deployment_with_init_status(
        app_name=APP_NAME,
        cluster=cluster,
        vantage_cluster_ctx=vantage_cluster_ctx,
        verbose=verbose,
        cloud=cloud,
        credential=cudo_credential,
        substrate=SUBSTRATE,
        additional_metadata={"credential_id": cudo_credential.id},
    )
    deployment.write()

    try:
        await _deploy_slurm_metal_cudo(vantage_cluster_ctx)
    except Exception as e:
        deployment.status = "error"
        deployment.write()
        ctx.obj.console.print(f"[bold red]Error:[/bold red] Deployment failed: {e}")
        return typer.Exit(code=1)

    deployment.status = "active"
    deployment.write()

    ctx.obj.console.print(success_create_message(deployment=deployment))
    return typer.Exit(0)


# Typer CLI commands
@handle_abort
@attach_settings
@attach_persona
@attach_vantage_rest_client
async def create_command(
    ctx: typer.Context,
    cluster_name: Annotated[
        str,
        typer.Argument(help="Name of the cluster to deploy"),
    ],
    dev_run: Annotated[
        bool, typer.Option("--dev-run", help="Use dummy cluster data for local development")
    ] = False,
) -> None:
    """Create a SLURM on metal Cluster and register it with Vantage."""
    cluster = generate_dev_cluster_data(cluster_name)

    if not dev_run:
        from vantage_cli.commands.cluster import utils as cluster_utils

        if (cluster := await cluster_utils.get_cluster_by_name(ctx, cluster_name)) is not None:
            if (extra_attrs := await get_extra_attributes(ctx)) is not None:
                if (sssd_binder_password := extra_attrs.get("sssd_binder_password")) is not None:
                    cluster.sssd_binder_password = sssd_binder_password
                else:
                    raise typer.Exit(code=1)
            else:
                raise typer.Exit(code=1)
        else:
            raise typer.Exit(code=1)

    await create(ctx=ctx, cluster=cluster)


async def _remove_slurm_metal_cudo(ctx: typer.Context, deployment: Deployment) -> None:
    """Remove a SLURM metal deployment Cudo Compute deployment.

    Args:
        ctx: Typer context containing console object
        deployment: Deployment object containing deployment information

    Raises:
        Exception: If cleanup fails
    """
    pass


async def remove(ctx: typer.Context, deployment: Deployment) -> None:
    """Remove a Multipass SLURM deployment by deleting the instance.

    Args:
        ctx: The typer context object for console access.
        deployment: The deployment object to remove

    Raises:
        Exception: If removal fails (non-critical, logged and continued)
    """
    await _remove_deployment(ctx=ctx, deployment=deployment)


@handle_abort
@attach_settings
async def remove_command(
    ctx: typer.Context,
    deployment_id: Annotated[
        str,
        typer.Argument(help="ID of the deployment to remove"),
    ],
) -> None:
    """Remove a Vantage LXD SLURM cluster."""
    deployment = await deployment_sdk.get_deployment(ctx, deployment_id)
    if deployment is not None:
        await remove(ctx=ctx, deployment=deployment)
        await deployment_sdk.delete(deployment.id)
        ctx.obj.console.print(f"[green]✓[/green] Deployment '{deployment.name}' removed successfully")
        return

    ctx.obj.console.print(f"[bold red]Error:[/bold red] Deployment '{deployment_id}' not found.")
    return


async def _remove_deployment(ctx: typer.Context, deployment: Deployment) -> None:
    """Internal function to remove a Cudo Compute SLURM on metal deployment.

    Args:
        ctx: The typer context object for console access.
        deployment: The deployment object to remove

    Raises:
        Exception: If removal fails (non-critical, logged and continued)
    """
    try:
        await _remove_slurm_metal_cudo(ctx, deployment)
    except Exception as e:
        logger.warning(f"Cudo Compute SLURM on metal failed: {e}")
        raise
    ctx.obj.console.print(success_destroy_message(deployment=deployment))


@attach_settings
@attach_persona
async def list_vm_datacenters_command(ctx: typer.Context) -> None:
    """List available Cudo Compute datacenters."""

    cudo_credential = cloud_credential_sdk.get_default(cloud_name=CLOUD)
    if cudo_credential is None:
        logger.debug(f"[bold red]Error:[/bold red] No default credential found for '{CLOUD}'")
        logger.debug(f"Run: vantage cloud credential create --cloud {CLOUD}")
        raise typer.Exit(code=1)

    # Initialize Cudo Compute SDK
    cudo_sdk = CudoComputeSDK(api_key=cudo_credential.credentials_data["api_key"])
    if cudo_sdk is None:
        logger.debug("[bold red]Error:[/bold red] Failed to initialize Cudo Compute SDK")
        raise typer.Exit(code=1)

    try:
        datacenters = await cudo_sdk.list_vm_data_centers()
    except Exception as e:
        logger.debug(f"[bold red]Error:[/bold red] Failed to list datacenters: {e}")
        raise typer.Exit(code=1)

    if not datacenters:
        logger.debug("No datacenters found.")
        return
    ctx.obj.formatter.render_list(
        data=datacenters,
        resource_name="Cudo Compute Datacenters",
    )


# Create typer app for this deployment app
from vantage_cli import AsyncTyper

app = AsyncTyper(
    name="slurm-metal-cudo",
    help="SLURM on Metal for Cudo Compute",
    no_args_is_help=True,
)

# Register commands
app.command("list-vm-datacenters", help="List available Cudo Compute datacenters")(
    list_vm_datacenters_command
)
