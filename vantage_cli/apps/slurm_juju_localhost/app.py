#!/usr/bin/env python3
# Copyright (c) 2025 Vantage Compute Corporation
# See LICENSE file for licensing details.
"""Juju localhost deployment app for Vantage CLI."""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import typer
import yaml
from juju.controller import Controller
from juju.errors import JujuError
from rich.console import Console
from rich.panel import Panel
from typing_extensions import Annotated

from vantage_cli.apps.common import validate_client_credentials, validate_cluster_data
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
    bundle_yaml = VANTAGE_JUPYTERHUB_YAML.copy()
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


async def deploy_juju_localhost(ctx: Any) -> None | typer.Exit:
    """Deploy Vantage JupyterHub SLURM cluster using Juju on localhost (refactored)."""
    console = Console()
    controller = Controller()
    model_name = "-".join(ctx.client_id.split("-")[:-4])
    secret_name = JUJU_SECRET_NAME
    try:
        console.print("Connecting to Juju controller...")
        await controller.connect()
        console.print(f"Creating juju model: {model_name}")
        model = await controller.add_model(model_name, cloud_name="localhost")
        try:
            console.print(f"Creating '{secret_name}' juju secret...")
            secret = await model.add_secret(secret_name, _build_secret_args(ctx))
            console.print(f"Secret created with ID: {secret}")
            console.print("Deploying SLURM cluster...")
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


async def deploy(ctx: typer.Context, cluster_data: Optional[Dict[str, Any]] = None) -> None:
    """Deploy Juju localhost SLURM cluster using cluster data.

    Args:
        ctx: Typer context containing CLI configuration
        cluster_data: Optional cluster configuration dictionary with client credentials

    Raises:
        typer.Exit: If deployment fails due to missing or invalid cluster data
    """
    console = Console()
    console.print(Panel("Juju Localhost SLURM Application"))
    console.print("Deploying juju localhost slurm application...")

    # Validate cluster data and extract credentials
    cluster_data = validate_cluster_data(cluster_data, console)
    client_id, client_secret = validate_client_credentials(cluster_data, console)

    # Get client secret from API if not in cluster data (import locally to avoid circular import)
    if not client_secret:
        from vantage_cli.commands.cluster import utils as cluster_utils

        client_secret = await cluster_utils.get_cluster_client_secret(ctx=ctx, client_id=client_id)

    # Check environment variable as fallback for client secret
    if not client_secret:
        client_secret = os.environ.get(ENV_CLIENT_SECRET, None)
    if not client_secret:
        console.print(
            "[red]Error: No client secret found in cluster data, API, or environment.[/red]"
        )
        raise typer.Exit(code=1)

    # Get jupyterhub_token from cluster data if available, otherwise generate a default
    jupyterhub_token = None
    if cluster_data and "creationParameters" in cluster_data:
        if jupyterhub_token_data := cluster_data["creationParameters"].get("jupyterhub_token"):
            jupyterhub_token = jupyterhub_token_data

    if jupyterhub_token is None:
        console.print("[red]Error: No jupyterhub_token found in cluster data.[/red]")
        raise typer.Exit(code=1)

    # Temporarily disabled for testing
    # vantage_cluster_context = VantageClusterContext(
    class MockContext:
        def __init__(self):
            self.client_id = client_id
            self.client_secret = client_secret
            self.base_api_url = "http://localhost:8000"  # dummy
            self.oidc_base_url = "http://localhost:8001"  # dummy
            self.oidc_domain = "localhost"  # dummy
            self.tunnel_api_url = "http://localhost:8002"  # dummy
            self.jupyterhub_token = jupyterhub_token

    vantage_cluster_context = MockContext()
    await deploy_juju_localhost(vantage_cluster_context)


# Typer CLI commands
@attach_settings
async def deploy_command(
    ctx: typer.Context,
    cluster_name: Annotated[
        str,
        typer.Argument(help="Name of the cluster to deploy"),
    ],
) -> None:
    """Deploy a Vantage JupyterHub SLURM cluster using Juju localhost."""
    console = Console()
    console.print(Panel("Juju Localhost SLURM Application"))
    console.print("Deploying juju localhost slurm application...")
    # Get cluster data by name - for now using local import to avoid circular imports
    from vantage_cli.commands.cluster import utils as cluster_utils

    cluster_data = await cluster_utils.get_cluster_by_name(ctx, cluster_name)

    # Fallback for testing if cluster not found
    if not cluster_data:
        console.print(
            f"[yellow]Warning: Cluster '{cluster_name}' not found. Using test configuration.[/yellow]"
        )
        cluster_data = {"clientId": "dummy_client_for_testing"}

    if not cluster_data:
        console.print("[red]Error: No cluster data found.[/red]")
        raise typer.Exit(code=1)

    await deploy(ctx=ctx, cluster_data=cluster_data)
