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
"""Juju localhost deployment app for Vantage CLI."""

import copy
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import typer
import yaml
from juju.controller import Controller
from juju.errors import JujuError
from rich.panel import Panel
from typing_extensions import Annotated

from vantage_cli.apps.common import (
    generate_dev_cluster_data,
    validate_client_credentials,
    validate_cluster_data,
)
from vantage_cli.commands.cluster.schema import VantageClusterContext
from vantage_cli.config import attach_settings
from vantage_cli.constants import (
    ENV_CLIENT_SECRET,
    JUJU_APPLICATION_NAME,
    JUJU_SECRET_NAME,
)

from .bundle_yaml import VANTAGE_JUPYTERHUB_YAML


def _build_secret_args(ctx: Any) -> list[str]:
    return [
        f"oidc-client-id={ctx.client_id}",
        f"oidc-client-secret={ctx.client_secret}",
        f"oidc-base-url={ctx.oidc_base_url}",
        f"tunnel-api-url={ctx.tunnel_api_url}",
        f"vantage-api-url={ctx.base_api_url}",
        f"oidc-domain={ctx.oidc_domain}",
        f"jupyterhub-token={ctx.jupyterhub_token}",
    ]


def _prepare_bundle(ctx: Any, model_name: str, secret_id: str) -> dict[str, Any]:
    bundle_yaml = copy.deepcopy(VANTAGE_JUPYTERHUB_YAML)
    bundle_yaml["applications"]["slurmctld"]["options"]["cluster-name"] = model_name
    va_opts = bundle_yaml["applications"]["vantage-agent"]["options"]
    jb_opts = bundle_yaml["applications"]["jobbergate-agent"]["options"]
    hub_opts = bundle_yaml["applications"]["vantage-jupyterhub"]["options"]

    va_opts["vantage-agent-base-api-url"] = ctx.base_api_url
    va_opts["vantage-agent-oidc-client-id"] = ctx.client_id
    va_opts["vantage-agent-oidc-domain"] = ctx.oidc_domain
    va_opts["vantage-agent-oidc-client-secret"] = ctx.client_secret
    va_opts["vantage-agent-cluster-name"] = model_name

    jb_opts["jobbergate-agent-base-api-url"] = ctx.base_api_url
    jb_opts["jobbergate-agent-oidc-domain"] = ctx.oidc_domain
    jb_opts["jobbergate-agent-oidc-client-id"] = ctx.client_id
    jb_opts["jobbergate-agent-oidc-client-secret"] = ctx.client_secret

    hub_opts["vantage-jupyterhub-config-secret-id"] = secret_id
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
            await model.deploy("./bundle.yaml")
        finally:
            os.chdir(original_cwd)


async def _run_slurmd_node_configured(model) -> None:
    if slurmd_app := model.applications.get("slurmd"):
        if slurmd_units := slurmd_app.units:
            for slurmd_unit in slurmd_units:
                action = await slurmd_unit.run_action("node-configured")
                await action.wait()
                print(f"Action result for {slurmd_unit.name}: {action.results}")


async def _configure_jobbergate_influxdb(model) -> None:
    slurmctld_app = model.applications.get("slurmctld")
    if not slurmctld_app or not slurmctld_app.units:
        print("Warning: slurmctld application not found")
        return
    leader_unit = None
    for unit in slurmctld_app.units:
        if await unit.is_leader_from_status():
            leader_unit = unit
        break
    if leader_unit is None:
        print("Warning: Could not find slurmctld leader unit")
        return
    action = await leader_unit.run("sudo cat /etc/slurm/acct_gather.conf")
    await action.wait()
    if action.results.get("return-code") != 0:
        print(
            f"Warning: Failed to get InfluxDB config: {action.results.get('stderr', 'Unknown error')}"
        )
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
    print(f"Parsed InfluxDB config: host={host}, user={user}, db={db}, rp={rp}")
    if not all([user, pw, host, db, rp]):
        print("Warning: Could not parse complete InfluxDB configuration")
        return
    influxdb_uri = f"influxdb://{user}:{pw}@{host}/{db}?rp={rp}"
    jobbergate_agent = model.applications.get("jobbergate-agent")
    if not jobbergate_agent:
        print("Warning: jobbergate-agent application not found")
        return
    await jobbergate_agent.set_config({"jobbergate-agent-influx-dsn": influxdb_uri})
    print("InfluxDB configuration applied to jobbergate-agent")


async def deploy_juju_localhost(ctx: Any, deployment_name: str) -> None | typer.Exit:
    """Deploy Vantage JupyterHub SLURM cluster using Juju on localhost (refactored)."""
    controller = Controller()
    model_name = deployment_name  # Use deployment_name as model_name
    secret_name = JUJU_SECRET_NAME
    try:
        ctx.obj.console.print("Connecting to Juju controller...")
        await controller.connect()
        ctx.obj.console.print(f"Creating juju model: {model_name}")
        model = await controller.add_model(model_name, cloud_name="localhost")
        try:
            ctx.obj.console.print(f"Creating '{secret_name}' juju secret...")
            secret = await model.add_secret(secret_name, _build_secret_args(ctx))
            ctx.obj.console.print(f"Secret created with ID: {secret}")
            ctx.obj.console.print("Deploying SLURM cluster...")
            bundle_yaml = _prepare_bundle(ctx, model_name, secret)
            await _write_and_deploy_model_bundle(model, bundle_yaml)
            await model.grant_secret(secret_name, JUJU_APPLICATION_NAME)
            try:
                await model.wait_for_idle()
            except JujuError:
                return typer.Exit(code=1)
            await _run_slurmd_node_configured(model)
            await _configure_jobbergate_influxdb(model)
            print(
                f"'{model_name}' deployment complete!\nModel: {model_name}\nController: {controller.controller_name}"
            )
        finally:
            await model.disconnect()
    finally:
        await controller.disconnect()


async def deploy(ctx: typer.Context, cluster_data: Dict[str, Any]) -> None:
    """Deploy Juju localhost SLURM cluster using cluster data.

    Args:
        ctx: Typer context containing CLI configuration
        cluster_data: Optional cluster configuration dictionary with client credentials

    Raises:
        typer.Exit: If deployment fails due to missing or invalid cluster data
    """
    ctx.obj.console.print(Panel("Juju Localhost SLURM Application"))
    ctx.obj.console.print("Deploying juju localhost slurm application...")

    # Validate cluster data and extract credentials
    cluster_data = validate_cluster_data(cluster_data, ctx.obj.console)
    client_id, client_secret = validate_client_credentials(cluster_data, ctx.obj.console)

    # Get client secret from API if not in cluster data (import locally to avoid circular import)
    if not client_secret:
        from vantage_cli.commands.cluster import utils as cluster_utils

        client_secret = await cluster_utils.get_cluster_client_secret(ctx=ctx, client_id=client_id)

    # Check environment variable as fallback for client secret
    if not client_secret:
        client_secret = os.environ.get(ENV_CLIENT_SECRET, None)
    if not client_secret:
        ctx.obj.console.print(
            "[red]Error: No client secret found in cluster data, API, or environment.[/red]"
        )
        raise typer.Exit(code=1)

    # Get jupyterhub_token from cluster data if available, otherwise generate a default
    jupyterhub_token = None
    if cluster_data and "creationParameters" in cluster_data:
        if jupyterhub_token_data := cluster_data["creationParameters"].get("jupyterhub_token"):
            jupyterhub_token = jupyterhub_token_data

    if jupyterhub_token is None:
        ctx.obj.console.print("[red]Error: No jupyterhub_token found in cluster data.[/red]")
        raise typer.Exit(code=1)

    # Extract deployment name from cluster_data
    deployment_name = cluster_data.get("deployment_name", f"juju-{client_id[:8]}")

    # Get settings from the active profile (attached by @attach_settings decorator)
    settings = getattr(ctx.obj, "settings", None)
    if not settings:
        ctx.obj.console.print(
            "[red]Error: No settings found. Please configure your profile first.[/red]"
        )
        raise typer.Exit(code=1)

    # Create VantageClusterContext with the validated credentials and URLs from settings
    vantage_cluster_context = VantageClusterContext(
        client_id=client_id,
        client_secret=client_secret,
        base_api_url=settings.api_base_url,
        oidc_base_url=settings.oidc_base_url,
        oidc_domain=settings.oidc_domain,
        tunnel_api_url=settings.tunnel_api_url,
        jupyterhub_token=jupyterhub_token,
    )
    await deploy_juju_localhost(vantage_cluster_context, deployment_name)


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
    """Deploy a Vantage JupyterHub SLURM cluster using Juju localhost."""
    ctx.obj.console.print(Panel("Juju Localhost SLURM Application"))
    ctx.obj.console.print("Deploying juju localhost slurm application...")

    cluster_data = generate_dev_cluster_data(cluster_name)
    if not dev_run:
        from vantage_cli.commands.cluster import utils as cluster_utils

        cluster_data = await cluster_utils.get_cluster_by_name(ctx, cluster_name)
        if cluster_data is None:
            raise ValueError(f"Cluster '{cluster_name}' not found")
    else:
        ctx.obj.console.print(
            f"[blue]Using dev run mode with dummy cluster data for '{cluster_name}'[/blue]"
        )

    await deploy(ctx=ctx, cluster_data=cluster_data)


async def cleanup_juju_localhost(ctx: typer.Context, deployment_data: Dict[str, Any]) -> None:
    """Clean up a Juju localhost deployment by destroying the model.

    Args:
        ctx: Typer context containing console object
        deployment_data: Dictionary containing deployment information including deployment_name

    Raises:
        Exception: If cleanup fails
    """
    controller = Controller()

    # Get the deployment name (which is used as the model name)
    model_name = deployment_data.get("deployment_name", "")
    if not model_name:
        ctx.obj.console.print("[red]Error: No deployment_name found in deployment data[/red]")
        raise Exception("Missing deployment_name in deployment data")

    try:
        ctx.obj.console.print("Connecting to Juju controller...")
        await controller.connect()

        ctx.obj.console.print(f"[yellow]Destroying Juju model: {model_name}[/yellow]")
        await controller.destroy_model(model_name, destroy_storage=True)

        ctx.obj.console.print(f"[green]✓ Successfully destroyed Juju model '{model_name}'[/green]")

    except Exception as e:
        ctx.obj.console.print(f"[red]Error during cleanup: {e}[/red]")
        raise
    finally:
        try:
            await controller.disconnect()
        except Exception:
            pass  # Ignore disconnect errors
