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
"""Cudo Compute SLURM on K8S deployment app for Vantage CLI."""

import copy
import logging
from typing import Any

import typer
from typing_extensions import Annotated

from vantage_cli.auth import attach_persona
from vantage_cli.clouds.common import (
    create_deployment_with_init_status,
    generate_dev_cluster_data,
)
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.sdk.admin.management.organizations import get_extra_attributes
from vantage_cli.sdk.cluster.schema import Cluster, VantageClusterContext
from vantage_cli.sdk.deployment.crud import deployment_sdk
from vantage_cli.sdk.deployment.schema import Deployment
from vantage_cli.vantage_rest_api_client import attach_vantage_rest_client

from .constants import APP_NAME, SUBSTRATE
from .render import success_create_message, success_destroy_message

logger = logging.getLogger(__name__)


# TODO: Create bundle_yaml.py with VANTAGE_JUPYTERHUB_JUJU_BUNDLE_YAML
# For now, using a placeholder
VANTAGE_JUPYTERHUB_JUJU_BUNDLE_YAML: dict[str, Any] = {}


def _build_vantage_jupyterhub_secret_args(ctx: Any) -> list[str]:
    return [
        f"oidc-client-id={ctx.client_id}",
        f"oidc-client-secret={ctx.client_secret}",
        f"oidc-base-url={ctx.oidc_base_url}",
        f"tunnel-api-url={ctx.tunnel_api_url}",
        f"vantage-api-url={ctx.base_api_url}",
        f"oidc-domain={ctx.oidc_domain}",
        f"jupyterhub-token={ctx.jupyterhub_token}",
    ]


def _build_vantage_sssd_secret_args(ctx: Any) -> list[str]:
    return [
        f"sssd-binder-password={ctx.sssd_binder_password}",
        f"org-id={ctx.org_id}",
        f"ldap-url={ctx.ldap_url}",
    ]


def _prepare_bundle(
    ctx: Any,
    model_name: str,
    vantage_jupyterhub_config_secret_id: str,
    vantage_sssd_config_secret_id: str,
) -> dict[str, Any]:
    bundle_yaml = copy.deepcopy(VANTAGE_JUPYTERHUB_JUJU_BUNDLE_YAML)
    bundle_yaml["applications"]["slurmctld"]["options"]["cluster-name"] = model_name
    va_opts = bundle_yaml["applications"]["vantage-agent"]["options"]
    jb_opts = bundle_yaml["applications"]["jobbergate-agent"]["options"]
    hub_opts = bundle_yaml["applications"]["vantage-jupyterhub"]["options"]
    sssd_opts = bundle_yaml["applications"]["vantage-sssd"]["options"]

    va_opts["vantage-agent-base-api-url"] = ctx.base_api_url
    va_opts["vantage-agent-oidc-client-id"] = ctx.client_id
    va_opts["vantage-agent-oidc-domain"] = ctx.oidc_domain
    va_opts["vantage-agent-oidc-client-secret"] = ctx.client_secret
    va_opts["vantage-agent-cluster-name"] = model_name

    jb_opts["jobbergate-agent-base-api-url"] = ctx.base_api_url
    jb_opts["jobbergate-agent-oidc-domain"] = ctx.oidc_domain
    jb_opts["jobbergate-agent-oidc-client-id"] = ctx.client_id
    jb_opts["jobbergate-agent-oidc-client-secret"] = ctx.client_secret

    hub_opts["vantage-jupyterhub-config-secret-id"] = vantage_jupyterhub_config_secret_id
    sssd_opts["vantage-sssd-config-secret-id"] = vantage_sssd_config_secret_id
    return bundle_yaml


async def _configure_jobbergate_influxdb(model) -> None:
    slurmctld_app = model.applications.get("slurmctld")
    if not slurmctld_app or not slurmctld_app.units:
        return
    leader_unit = None
    for unit in slurmctld_app.units:
        if await unit.is_leader_from_status():
            leader_unit = unit
        break
    if leader_unit is None:
        return
    action = await leader_unit.run("sudo cat /etc/slurm/acct_gather.conf")
    await action.wait()
    if action.results.get("return-code") != 0:
        return
    influxdb_conf = action.results.get("stdout", "")
    host = user = pw = db = rp = None
    for line in influxdb_conf.splitlines():
        if line.startswith("profileinfluxdbhost"):
            host = line.split("=", 1)[1].strip()
        elif line.startswith("profileinfluxdbuser"):
            user = line.split("=", 1)[1].strip()
        elif line.startswith("profileinfluxdbpass"):
            pw = line.split("=", 1)[1].strip()
        elif line.startswith("profileinfluxdbdatabase"):
            db = line.split("=", 1)[1].strip()
        elif line.startswith("profileinfluxdbrtpolicy"):
            rp = line.split("=", 1)[1].strip()
    if not all([user, pw, host, db, rp]):
        return
    influxdb_uri = f"influxdb://{user}:{pw}@{host}/{db}?rp={rp}"
    jobbergate_agent = model.applications.get("jobbergate-agent")
    if not jobbergate_agent:
        return
    await jobbergate_agent.set_config({"jobbergate-agent-influx-dsn": influxdb_uri})


async def _deploy_slurm_k8s_cudo(ctx: Any) -> None:
    """Deploy SLURM on K8S using Cudo Compute.

    Args:
        ctx: VantageClusterContext containing deployment configuration

    Raises:
        Exception: If deployment fails
    """
    _build_vantage_jupyterhub_secret_args(ctx)
    _build_vantage_sssd_secret_args(ctx)


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

    from vantage_cli.sdk.cloud.crud import cloud_sdk

    cloud = cloud_sdk.get("cudo")
    if cloud is None:
        console.print("[bold red]Error:[/bold red] Cloud 'cudo' not found. Please debug")
        return typer.Exit(code=1)

    deployment = create_deployment_with_init_status(
        app_name=APP_NAME,
        cluster=cluster,
        vantage_cluster_ctx=vantage_cluster_ctx,
        verbose=verbose,
        cloud=cloud,
        substrate=SUBSTRATE,
    )
    deployment.write()

    try:
        await _deploy_slurm_k8s_cudo(vantage_cluster_ctx)
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
    """Create a SLURM on K8S Cluster and register it with Vantage."""
    cluster = generate_dev_cluster_data(cluster_name)

    if not dev_run:
        from vantage_cli.sdk.cluster.crud import cluster_sdk

        if (cluster := await cluster_sdk.get_cluster_by_name(ctx, cluster_name)) is not None:
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


async def _remove_slurm_k8s_cudo(ctx: typer.Context, deployment: Deployment) -> None:
    """Remove a SLURM K8S deployment Cudo Compute deployment.

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
    """Remove a Cudo Compute SLURM on K8s deployment.

    Args:
        ctx: The typer context object for console access.
        deployment: The deployment object to remove

    Raises:
        Exception: If removal fails (non-critical, logged and continued)
    """
    try:
        await _remove_slurm_k8s_cudo(ctx, deployment)
    except Exception as e:
        logger.warning(f"Cudo Compute SLURM on K8S failed: {e}")
        raise
    ctx.obj.console.print(success_destroy_message(deployment=deployment))
