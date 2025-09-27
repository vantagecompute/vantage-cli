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

import logging
from typing import Annotated, Optional

import typer
from cudo_compute_sdk import CudoComputeSDK

from vantage_cli.auth import attach_persona
from vantage_cli.clouds.common import (
    create_deployment_with_init_status,
    generate_dev_cluster_data,
)
from vantage_cli.clouds.cudo_compute.apps.slurm_metal.constants import CLOUD
from vantage_cli.clouds.cudo_compute.apps.slurm_metal.templates import (
    head_node_init_script,
)
from vantage_cli.clouds.cudo_compute.apps.slurm_metal.utils import init_project_and_head_node
from vantage_cli.clouds.cudo_compute.cmds import attach_cudo_compute_client
from vantage_cli.clouds.cudo_compute.utils import get_datacenter_id_from_credentials
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.sdk.admin.management.organizations import get_extra_attributes
from vantage_cli.sdk.cloud.crud import cloud_sdk
from vantage_cli.sdk.cloud_credential.crud import cloud_credential_sdk
from vantage_cli.sdk.cloud_credential.schema import CloudCredential
from vantage_cli.sdk.cluster.schema import Cluster, VantageClusterContext
from vantage_cli.sdk.deployment.crud import deployment_sdk
from vantage_cli.sdk.deployment.schema import Deployment
from vantage_cli.vantage_rest_api_client import attach_vantage_rest_client

from .constants import APP_NAME, SUBSTRATE
from .render import success_create_message, success_destroy_message

logger = logging.getLogger("vantage_cli.clouds.cudo_compute.apps.slurm_metal")


async def _deploy_slurm_metal_cudo(
    ctx: typer.Context, vantage_cluster_ctx: VantageClusterContext, deployment: Deployment
) -> None:
    """Deploy SLURM on metal using Cudo Compute.

    Args:
        ctx: Typer context containing CLI configuration and Cudo SDK
        vantage_cluster_ctx: Context containing cluster configuration and state
        deployment: Deployment object with metadata and configuration

    Raises:
        Exception: If deployment fails
    """
    cudo_sdk = ctx.obj.cudo_sdk

    logger.debug(f"{await cudo_sdk.whoami()}")

    if deployment.additional_metadata is None:
        raise Exception("Deployment missing additional_metadata")

    default_datacenter_id = deployment.additional_metadata.get("default_datacenter_id")
    if default_datacenter_id is None:
        raise Exception("Missing default_datacenter_id in deployment metadata")

    slurm_head_node_init_script = head_node_init_script(
        vantage_cluster_ctx=vantage_cluster_ctx,
        cudo_ctx={"api_key": cudo_sdk.api_key, "data_center_id": default_datacenter_id},
    )
    from pathlib import Path

    Path("/home/bdx/slurm_head_node_init_script_1.sh").write_text(slurm_head_node_init_script)
    vm_id = await init_project_and_head_node(
        ctx,
        project_name=deployment.name,
        init_script=slurm_head_node_init_script,
        data_center_id=default_datacenter_id,
    )
    logger.debug(f"Created head node VM: {vm_id}")


async def create(ctx: typer.Context, cluster: Cluster) -> typer.Exit:
    """Create Juju localhost Charmed HPC cluster using cluster data.

    Args:
        ctx: Typer context containing CLI configuration
        cluster: Cluster object with configuration and client credentials

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

    cudo_credential: Optional[CloudCredential] = cloud_credential_sdk.get_default(cloud_name=CLOUD)
    if cudo_credential is None:
        console.print(f"[bold red]Error:[/bold red] No default credential found for '{CLOUD}'")
        console.print(f"[dim]Run: vantage cloud credential create --cloud {CLOUD}[/dim]")
        return typer.Exit(code=1)

    cudo_datacenter_id = get_datacenter_id_from_credentials()
    if cudo_datacenter_id is None:
        console.print(f"[bold red]Error:[/bold red] No default datacenter found for '{CLOUD}'")
        console.print(f"[dim]Run: vantage cloud datacenter create --cloud {CLOUD}[/dim]")
        return typer.Exit(code=1)

    # Get the Cudo Compute cloud configuration
    cloud = cloud_sdk.get(CLOUD)
    if cloud is None:
        console.print(f"[bold red]Error:[/bold red] Cloud '{CLOUD}' not found. Please debug")
        return typer.Exit(code=1)

    deployment = create_deployment_with_init_status(
        app_name=APP_NAME,
        cluster=cluster,
        vantage_cluster_ctx=vantage_cluster_ctx,
        verbose=verbose,
        cloud=cloud,
        credential=cudo_credential,
        substrate=SUBSTRATE,
        additional_metadata={"default_datacenter_id": cudo_datacenter_id},
    )
    deployment.write()

    try:
        await _deploy_slurm_metal_cudo(ctx, vantage_cluster_ctx, deployment)
    except Exception as e:
        deployment.status = "error"
        deployment.write()
        ctx.obj.console.print(f"[bold red]Error:[/bold red] Deployment failed: {e}")
        return typer.Exit(code=1)

    deployment.status = "active"
    deployment.write()

    ctx.obj.console.print(success_create_message(deployment=deployment))
    return typer.Exit(0)


@handle_abort
@attach_settings
@attach_persona
@attach_vantage_rest_client
@attach_cudo_compute_client
async def create_command(
    ctx: typer.Context,
    cluster_name: Annotated[
        str,
        typer.Argument(help="Name of the cluster to deploy"),
    ],
    dev_run: Annotated[
        bool, typer.Option("--dev-run", help="Use dummy cluster data for local development")
    ] = False,
) -> Optional[typer.Exit]:
    """Create a SLURM on metal Cluster and register it with Vantage."""
    cluster = generate_dev_cluster_data(cluster_name)

    if not dev_run:
        from vantage_cli.sdk.cluster.crud import cluster_sdk

        if (cluster := await cluster_sdk.get_cluster_by_name(ctx, cluster_name)) is not None:
            if (extra_attrs := await get_extra_attributes(ctx)) is not None:
                if (sssd_binder_password := extra_attrs.get("sssd_binder_password")) is not None:
                    cluster.sssd_binder_password = sssd_binder_password
                else:
                    return typer.Exit(code=1)
            else:
                return typer.Exit(code=1)
        else:
            return typer.Exit(code=1)

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
        ctx.obj.console.print(
            f"[green]✓[/green] Deployment '{deployment.name}' removed successfully"
        )
        return

    ctx.obj.console.print(f"[bold red]Error:[/bold red] Deployment '{deployment_id}' not found.")
    return


async def _remove_deployment(ctx: typer.Context, deployment: Deployment) -> None:
    """Remove a Cudo Compute SLURM on metal deployment.

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
async def list_vm_datacenters_command(ctx: typer.Context) -> Optional[typer.Exit]:
    """List available Cudo Compute datacenters."""
    cudo_credential = cloud_credential_sdk.get_default(cloud_name=CLOUD)
    if cudo_credential is None:
        logger.debug(f"[bold red]Error:[/bold red] No default credential found for '{CLOUD}'")
        logger.debug(f"Run: vantage cloud credential create --cloud {CLOUD}")
        return typer.Exit(code=1)

    # Initialize Cudo Compute SDK
    cudo_sdk = CudoComputeSDK(api_key=cudo_credential.credentials_data["api_key"])

    try:
        datacenters = await cudo_sdk.list_vm_data_centers()
    except Exception as e:
        logger.debug(f"[bold red]Error:[/bold red] Failed to list datacenters: {e}")
        return typer.Exit(code=1)

    if not datacenters:
        logger.debug("No datacenters found.")
        return
    ctx.obj.formatter.render_list(
        data=datacenters,
        resource_name="Cudo Compute Datacenters",
    )
