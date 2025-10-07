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
"""LXD/Juju localhost deployment app for Vantage CLI."""

import asyncio
import copy
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import typer
import yaml
from juju.controller import Controller
from juju.errors import JujuError
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
from vantage_cli.apps.constants import DEV_JUPYTERHUB_TOKEN, DEV_SSSD_BINDER_PASSWORD
from vantage_cli.apps.slurm_lxd_localhost.utils import (
    SuppressOutput,
    check_juju_available,
)
from vantage_cli.config import attach_settings
from vantage_cli.constants import (
    CLOUD_TYPE_CONTAINER,
)
from vantage_cli.exceptions import handle_abort
from vantage_cli.sdk.cluster.schema import VantageClusterContext

from .bundle_yaml import VANTAGE_JUPYTERHUB_YAML
from .constants import (
    APP_NAME,
    CLOUD as CLOUD_LOCALHOST,
    JUPYTERHUB_APPLICATION_NAME,
    JUPYTERHUB_SECRET_NAME,
    SSSD_APPLICATION_NAME,
    SSSD_SECRET_NAME,
)
from .render import success_create_message, success_destroy_message


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

def _prepare_bundle(ctx: Any, model_name: str, vantage_jupyterhub_config_secret_id: str, vantage_sssd_config_secret_id: str) -> dict[str, Any]:
    bundle_yaml = copy.deepcopy(VANTAGE_JUPYTERHUB_YAML)
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


async def _write_and_deploy_model_bundle(model, bundle_yaml: dict[str, Any]) -> None:
    original_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as td:
        f_name = Path(td) / "bundle.yaml"
        with open(f_name, "w") as fh:
            fh.write(yaml.dump(bundle_yaml))
        Path(td).chmod(0o700)
        os.chdir(td)
        try:
            with SuppressOutput():
                # Add timeout to prevent hanging indefinitely on bundle deployment
                await asyncio.wait_for(
                    model.deploy("./bundle.yaml"), timeout=120
                )  # 2 minutes timeout
        finally:
            os.chdir(original_cwd)


async def _run_slurmd_node_configured(model) -> None:
    if slurmd_app := model.applications.get("slurmd"):
        if slurmd_units := slurmd_app.units:
            for slurmd_unit in slurmd_units:
                action = await slurmd_unit.run_action("node-configured")
                await action.wait()


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


async def deploy_juju_localhost(vantage_ctx: Any, deployment_name: str) -> None | typer.Exit:
    """Deploy Vantage JupyterHub Charmed HPC cluster using Juju on localhost (refactored)."""

    controller = Controller()
    model_name = deployment_name  # Use deployment_name as model_name

    try:
        await controller.connect()

        model = await controller.add_model(model_name, cloud_name="localhost")

        vantage_jupyterhub_config_secret_id = await model.add_secret(
            JUPYTERHUB_SECRET_NAME,
            _build_vantage_jupyterhub_secret_args(vantage_ctx)
        )

        vantage_sssd_config_secret_id = await model.add_secret(
        SSSD_SECRET_NAME,
            _build_vantage_sssd_secret_args(vantage_ctx)
        )

        bundle_yaml = _prepare_bundle(
            vantage_ctx,
            model_name=model_name,
            vantage_jupyterhub_config_secret_id=vantage_jupyterhub_config_secret_id,
            vantage_sssd_config_secret_id=vantage_sssd_config_secret_id,
        )

        await _write_and_deploy_model_bundle(model, bundle_yaml)

        await model.grant_secret(JUPYTERHUB_SECRET_NAME, JUPYTERHUB_APPLICATION_NAME)
        await model.grant_secret(SSSD_SECRET_NAME, SSSD_APPLICATION_NAME)

        await model.wait_for_idle()

        await _run_slurmd_node_configured(model)

        await _configure_jobbergate_influxdb(model)

        await model.disconnect()
        await controller.disconnect()

    except JujuError as _:
        return typer.Exit(code=1)


async def create(
    ctx: typer.Context, cluster_data: Dict[str, Any]) -> None | typer.Exit:
    """Create Juju localhost Charmed HPC cluster using cluster data.

    Args:
        ctx: Typer context containing CLI configuration
        cluster_data: Cluster configuration dictionary with client credentials

    Raises:
        typer.Exit: If deployment fails due to missing or invalid cluster data
    """
    console = ctx.obj.console
    verbose = ctx.obj.verbose
    settings = ctx.obj.settings

    org_id = ctx.obj.persona.identity_data.org_id

    cluster_name = cluster_data["name"]
    
    # Validate and fetch client credentials
    client_id, client_secret = validate_client_credentials(cluster_data, console)
    
    # Import locally to avoid circular import
    from vantage_cli.commands.cluster.utils import get_cluster_client_secret
    client_secret = await get_cluster_client_secret(ctx=ctx, client_id=client_id)
    
    deployment_id = generate_default_deployment_name(APP_NAME, cluster_name)

    sssd_binder_password = get_sssd_binder_password(cluster_data)
    jupyterhub_token = get_jupyterhub_token(cluster_data)

    create_deployment_with_init_status(
        deployment_id=deployment_id,
        app_name=APP_NAME,
        cluster_name=cluster_name,
        cluster_data=cluster_data,
        console=console,
        verbose=verbose,
        cloud=CLOUD_LOCALHOST,
        cloud_type=CLOUD_TYPE_CONTAINER,
    )

    vantage_ctx = VantageClusterContext(
        cluster_name=cluster_name,
        client_id=client_id,
        client_secret=client_secret or DEV_CLIENT_SECRET,
        base_api_url=settings.get_apis_url(),
        oidc_base_url=settings.get_auth_url(),
        oidc_domain=settings.oidc_domain,
        tunnel_api_url=settings.get_tunnel_url(),
        jupyterhub_token=jupyterhub_token or DEV_JUPYTERHUB_TOKEN,
        sssd_binder_password=sssd_binder_password or DEV_SSSD_BINDER_PASSWORD,
        ldap_url=settings.get_ldap_url(),
        org_id=org_id,
    )
    try:
        await deploy_juju_localhost(vantage_ctx, deployment_id)
    except Exception as e:
        update_deployment_status(deployment_id, "error", console, verbose=verbose)
        console.print(f"[bold red]Error:[/bold red] Deployment failed: {e}")
        return typer.Exit(code=1)
    
    update_deployment_status(deployment_id, "active", console, verbose=verbose)
    console.print(success_create_message(
        cluster_name=cluster_name,
        client_id=cluster_data["clientId"],
        deployment_id=deployment_id,
    ))
    return typer.Exit(0)


# Typer CLI commands
@handle_abort
@attach_settings
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
    """Create a Charmed HPC SLURM cluster using Juju on localhost and register it with Vantage."""
    # Check for Juju early before doing any other work
    check_juju_available()

    # Import cluster_utils locally to avoid circular import
    from vantage_cli.commands.cluster import utils as cluster_utils

    cluster_data = generate_dev_cluster_data(cluster_name)
    cluster_data["clientSecret"] = DEV_CLIENT_SECRET

    if not dev_run:
        if (cluster_data := await cluster_utils.get_cluster_by_name(ctx, cluster_name)) is not None:
            if (client_id := cluster_data.get("clientId")) is not None:
                if (client_secret := await cluster_utils.get_cluster_client_secret(ctx=ctx, client_id=client_id)) is not None:
                    cluster_data["clientSecret"] = client_secret

    await create(ctx=ctx, cluster_data=cluster_data)


async def remove_juju_localhost(ctx: typer.Context, deployment_data: Dict[str, Any]) -> None:
    """Remove a Juju localhost deployment by destroying the model.

    Args:
        ctx: Typer context containing console object
        deployment_data: Dictionary containing deployment information including deployment_name and deployment_id

    Raises:
        Exception: If cleanup fails
    """
    console = ctx.obj.console

    controller = Controller()
    model_name = deployment_data.get("deployment_name", "")

    try:
        await controller.connect()
        await controller.destroy_model(model_name, destroy_storage=True)
        final_success_message = success_destroy_message(cluster_name=model_name)
        console.print(final_success_message)
    except Exception as e:
        update_deployment_status(deployment_data.get("deployment_id", ""), "error", console, verbose=ctx.obj.verbose)
        console.print(f"[bold red]Error:[/bold red] Failed to remove deployment: {e}")
        raise
    finally:
        try:
            await controller.disconnect()
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] Failed to disconnect controller: {e}")
            pass
