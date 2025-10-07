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
    update_deployment_status,
    validate_client_credentials,
    validate_cluster_data,
)
from vantage_cli.apps.slurm_lxd_localhost.utils import (
    SuppressOutput,
    check_juju_available,
    is_ready,
)
from vantage_cli.commands.cluster import utils as cluster_utils
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
from vantage_cli.render import RenderStepOutput

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

def _prepare_bundle(ctx: Any, model_name: str, vantage_jupyterhub_secret_id: str, vantage_sssd_secret_id: str) -> dict[str, Any]:
    bundle_yaml = copy.deepcopy(VANTAGE_JUPYTERHUB_YAML)
    bundle_yaml["applications"]["slurmctld"]["options"]["cluster-name"] = model_name
    va_opts = bundle_yaml["applications"]["vantage-agent"]["options"]
    jb_opts = bundle_yaml["applications"]["jobbergate-agent"]["options"]
    hub_opts = bundle_yaml["applications"]["vantage-jupyterhub"]["options"]
    sssd_opts = bundle_yaml["applications"]["vantage-sssd"]["options"]

    va_opts["vantage-agent-base-api-url"] = ctx.api_url
    va_opts["vantage-agent-oidc-client-id"] = ctx.client_id
    va_opts["vantage-agent-oidc-domain"] = ctx.oidc_domain
    va_opts["vantage-agent-oidc-client-secret"] = ctx.client_secret
    va_opts["vantage-agent-cluster-name"] = model_name

    jb_opts["jobbergate-agent-base-api-url"] = ctx.api_url
    jb_opts["jobbergate-agent-oidc-domain"] = ctx.oidc_domain
    jb_opts["jobbergate-agent-oidc-client-id"] = ctx.client_id
    jb_opts["jobbergate-agent-oidc-client-secret"] = ctx.client_secret

    hub_opts["vantage-jupyterhub-config-secret-id"] = vantage_jupyterhub_secret_id
    sssd_opts["vantage-sssd-config-secret-id"] = vantage_sssd_secret_id
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

        vantage_jupyterhub_secret_id = await model.add_secret(
            JUPYTERHUB_SECRET_NAME,
            _build_vantage_jupyterhub_secret_args(vantage_ctx)
        )

        vantage_sssd_secret_id = await model.add_secret(
        SSSD_SECRET_NAME,
            _build_vantage_sssd_secret_args(vantage_ctx)
        )

        bundle_yaml = _prepare_bundle(
            vantage_ctx,
            model_name=model_name,
            vantage_jupyterhub_secret_id=vantage_jupyterhub_secret_id,
            vantage_sssd_secret_id=vantage_sssd_secret_id,
        )

        await _write_and_deploy_model_bundle(model, bundle_yaml)

        await model.grant_secret(vantage_jupyterhub_secret_id, JUPYTERHUB_APPLICATION_NAME)
        await model.grant_secret(vantage_sssd_secret_id, SSSD_APPLICATION_NAME)

        await model.wait_for_idle()

        await _run_slurmd_node_configured(model)

        await _configure_jobbergate_influxdb(model)

        await model.disconnect()
        await controller.disconnect()

    except JujuError as e:
        return typer.Exit(code=1)


async def create(
    ctx: typer.Context, cluster_data: Dict[str, Any], dev_run: bool = False
) -> None:
    """Create Juju localhost Charmed HPC cluster using cluster data.

    Args:
        ctx: Typer context containing CLI configuration
        cluster_data: Optional cluster configuration dictionary with client credentials
        dev_run: Whether this is a development run with dummy data

    Raises:
        typer.Exit: If deployment fails due to missing or invalid cluster data
    """
    console = ctx.obj.console
    verbose = getattr(ctx.obj, "verbose", False)
    cluster_data = validate_cluster_data(cluster_data, console)

    client_id, client_secret = validate_client_credentials(cluster_data, console)

    if verbose:
        console.print(f"[debug]DEBUG: client_id={client_id}, has_client_secret={bool(client_secret)}")

    # Get client secret from API if not in cluster data (but skip for dev runs)
    if not client_secret and not dev_run:
        if verbose:
            console.print("[debug]DEBUG: Getting client secret from API (not dev run)")

        client_secret = await cluster_utils.get_cluster_client_secret(ctx=ctx, client_id=client_id)
        if verbose:
            console.print(f"[debug]DEBUG: Got client secret from API: {bool(client_secret)}")

    elif not client_secret and dev_run:
        if verbose:
            console.print("[debug]DEBUG: Skipping client secret API call (dev run mode)")
        client_secret = "dev-mode-placeholder"
    else:
        if verbose:
            console.print("[debug]DEBUG: Already have client secret, no API call needed")

    # Generate deployment ID and create deployment with init status
    cluster_name = cluster_data.get("name", "unknown")
    deployment_id = generate_default_deployment_name(APP_NAME, cluster_name)
    if verbose:
        console.print(f"[debug]DEBUG: deployment_id={deployment_id}, cluster_name={cluster_name}")

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

    # Define deployment steps
    steps = [
        DeploymentStep("Initialize deployment"),
        DeploymentStep("Check Juju availability"),
        DeploymentStep("Validate cluster credentials"),
        DeploymentStep("Connect to Juju controller"),
        DeploymentStep("Deploy bundle"),
        DeploymentStep("Configure cluster"),
        DeploymentStep("Finalize deployment"),
    ]

    deployment_success = False

    # Create final success message for the panel
    final_success_message = f"""🎉 [bold green]Charmed HPC Juju deployment completed successfully![/bold green]

Access your cluster in the Vantage UI: [cyan]https://app.vantagecompute.ai/compute/clusters/{client_id}[/cyan]

[bold]Deployment Summary:[/bold]
• Juju controller: [cyan]{cluster_name}-controller[/cyan]
• Juju model: [cyan]{cluster_name}-model[/cyan]
• Deployment ID: [cyan]{deployment_id}[/cyan]
• Container environment: [cyan]LXD containers[/cyan]

[bold]Connect to Charmed HPC Cluster:[/bold]
• SLURM controller: [cyan]juju ssh slurmctld/0[/cyan]
• SLURM compute node: [cyan]juju ssh slurmd/0[/cyan]
• JupyterHub interface: [cyan]juju ssh jupyterhub/0[/cyan]

[bold]Access Web Interfaces:[/bold]
• Get JupyterHub URL: [cyan]juju status jupyterhub --format=json | jq -r '.applications.jupyterhub.units | to_entries[0].value["public-address"]'[/cyan]
• JupyterHub access: [cyan]http://<jupyterhub-ip>:8000[/cyan]
• SLURM job submission: Available via JupyterHub terminal or SSH to slurmctld

[bold]Monitoring & Management:[/bold]
• Check all services: [cyan]juju status[/cyan]
• Monitor deployment: [cyan]juju status --watch 5s[/cyan]
• View application logs: [cyan]juju debug-log[/cyan]
• Monitor SLURM controller: [cyan]juju debug-log --include=slurmctld/0[/cyan]
• Monitor compute nodes: [cyan]juju debug-log --include=slurmd[/cyan]
• Check JupyterHub logs: [cyan]juju debug-log --include=jupyterhub/0[/cyan]

[bold]SLURM Job Management:[/bold]
• Submit test job: [cyan]juju ssh slurmctld/0 -- sinfo[/cyan]
• Check queue: [cyan]juju ssh slurmctld/0 -- squeue[/cyan]
• Node status: [cyan]juju ssh slurmctld/0 -- scontrol show nodes[/cyan]

[bold]Other Useful Commands:[/bold]
• Check cluster status: [cyan]vantage deployment slurm-juju-localhost status[/cyan]
• Scale compute nodes: [cyan]juju add-unit slurmd[/cyan]
• Remove deployment: [cyan]vantage deployment slurm-juju-localhost remove[/cyan]
• Access Juju GUI: [cyan]juju gui[/cyan]

[yellow]Note:[/yellow] Use 'juju status' to monitor deployment progress. All services run in LXD containers."""

    try:
        with deployment_progress_panel(
            steps=steps,
            console=console,
            verbose=False,  # Always use panel mode for clean display
            title="Deploying Charmed HPC Cluster",
            panel_title="🚀 Charmed HPC Deployment Progress",
            final_message=final_success_message,
        ) as advance_step:
            if verbose:
                console.print("[debug]DEBUG: Starting deployment with dev_run =", dev_run)
            advance_step("Initialize deployment", "starting")
            if verbose:
                console.print("[debug]DEBUG: Initialize deployment step started")
            advance_step("Initialize deployment", "completed")
            if verbose:
                console.print("[debug]DEBUG: Initialize deployment step completed")

            advance_step("Check Juju availability", "starting")
            if verbose:
                console.print("[debug]DEBUG: About to check Juju availability")
            # Check for Juju early before doing any other work
            check_juju_available()
            if verbose:
                console.print("[debug]DEBUG: Juju availability check completed")
            advance_step("Check Juju availability", "completed")

            advance_step("Validate cluster credentials", "starting")
            if verbose:
                console.print("[debug]DEBUG: Starting credential validation")
            # Client credentials already validated at start of function
            
            # Validate we have client secret
            if not client_secret:
                if verbose:
                    console.print("[debug]DEBUG: No client secret available")
                advance_step("Validate cluster credentials", "failed")
                raise RuntimeError("No client secret found in cluster data or API.")
            
            if verbose:
                console.print("[debug]DEBUG: Client secret check - has secret:", bool(client_secret))

            # Get jupyterhub_token from cluster data if available
            jupyterhub_token = None
            if verbose:
                console.print(
                    "[debug]DEBUG: Checking cluster_data for jupyterhub_token:", bool(cluster_data)
                )
            if cluster_data and "creationParameters" in cluster_data:
                if verbose:
                    console.print(
                        f"[debug]DEBUG: creationParameters keys: {list(cluster_data['creationParameters'].keys())}"
                    )
                # After GraphQL conversion, keys are in snake_case
                jupyterhub_token = cluster_data["creationParameters"].get("jupyterhub_token")
                if jupyterhub_token and verbose:
                    console.print("[debug]DEBUG: Found jupyterhub_token in cluster data")
            else:
                if verbose:
                    console.print("[debug]DEBUG: No creationParameters in cluster_data")

            if verbose:
                console.print(
                    "[debug]DEBUG: Jupyterhub token check - has token:", bool(jupyterhub_token)
                )
            if jupyterhub_token is None:
                if verbose:
                    console.print("[debug]DEBUG: No jupyterhub_token found")
                advance_step("Validate cluster credentials", "failed")
                raise RuntimeError("No jupyterhub_token found in cluster data.")

            if verbose:
                console.print("[debug]DEBUG: Credential validation completed successfully")
            advance_step("Validate cluster credentials", "completed")

            advance_step("Connect to Juju controller", "starting")
            if verbose:
                console.print("[debug]DEBUG: Starting Juju controller connection")
            # Extract deployment name from cluster_data
            deployment_name = cluster_data.get("deployment_name", client_id)
            if verbose:
                console.print("[debug]DEBUG: Deployment name:", deployment_name)

            # Get settings from the active profile (attached by @attach_settings decorator)
            settings = getattr(ctx.obj, "settings", None)
            if verbose:
                console.print("[debug]DEBUG: Settings found:", bool(settings))
            if not settings:
                if verbose:
                    console.print("[debug]DEBUG: No settings found")
                advance_step("Connect to Juju controller", "failed")
                raise RuntimeError("No settings found. Please configure your profile first.")

            # Create VantageClusterContext with the validated credentials and URLs from settings
            if verbose:
                console.print("[debug]DEBUG: Creating VantageClusterContext")

            # Get org_id from profile, with fallback for dev mode
            org_id = "dev-org-id"
            if hasattr(ctx.obj, 'profile') and hasattr(ctx.obj.profile, 'identity_data'):
                org_id = ctx.obj.profile.identity_data.org_id

            vantage_cluster_context = VantageClusterContext(
                cluster_name=cluster_name,
                client_id=client_id,
                client_secret=client_secret,
                base_api_url=settings.get_apis_url(),
                oidc_base_url=settings.get_auth_url(),
                oidc_domain=settings.oidc_domain,
                tunnel_api_url=settings.get_tunnel_url(),
                jupyterhub_token=jupyterhub_token,
                sssd_binder_password="ratsrats",
                ldap_url=settings.get_ldap_url(),
                org_id=org_id,
            )
            if verbose:
                console.print("[debug]DEBUG: VantageClusterContext created successfully")
            advance_step("Connect to Juju controller", "completed")

            advance_step("Deploy bundle", "starting")
            if verbose:
                console.print("[debug]DEBUG: Starting deploy bundle step")
            advance_step("Configure cluster", "starting")
            if verbose:
                console.print("[debug]DEBUG: Starting configure cluster step")

            # Call the actual deployment function
            try:
                if verbose:
                    console.print("[debug]DEBUG: About to call deploy_juju_localhost")
                await deploy_juju_localhost(vantage_cluster_context, deployment_name)
                if verbose:
                    console.print("[debug]DEBUG: deploy_juju_localhost completed successfully")
                advance_step("Deploy bundle", "completed")
                advance_step("Configure cluster", "completed")
                if verbose:
                    console.print("[debug]DEBUG: Deploy and configure steps marked as completed")
            except Exception as e:
                if verbose:
                    console.print(f"[debug]DEBUG: Exception in deploy_juju_localhost: {str(e)}")
                advance_step("Deploy bundle", "failed")
                advance_step("Configure cluster", "failed")
                raise RuntimeError(f"Deployment failed: {str(e)}")

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
        
        # Print the actual error so we can debug
        console.print(f"[red]ERROR: Deployment failed with exception: {str(e)}[/red]")
        import traceback
        if verbose:
            console.print(f"[red]{traceback.format_exc()}[/red]")

        raise typer.Exit(1)


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

    cluster_data = generate_dev_cluster_data(cluster_name)
    if not dev_run:
        from vantage_cli.commands.cluster import utils as cluster_utils

        cluster_data = await cluster_utils.get_cluster_by_name(ctx, cluster_name)
        if cluster_data is None:
            raise ValueError(f"Cluster '{cluster_name}' not found")

    await create(ctx=ctx, cluster_data=cluster_data, dev_run=dev_run)


async def remove_juju_localhost(
    ctx: typer.Context, deployment_data: Dict[str, Any], verbose: bool = False
) -> None:
    """Remove a Juju localhost deployment by destroying the model.

    Args:
        ctx: Typer context containing console object
        deployment_data: Dictionary containing deployment information including deployment_name
        verbose: Whether to show verbose output

    Raises:
        Exception: If cleanup fails
    """
    console = ctx.obj.console
    controller = Controller()

    # Get the deployment name (which is used as the model name)
    model_name = deployment_data.get("deployment_name", "")
    if not model_name:
        raise Exception("Missing deployment_name in deployment data")

    # Get deployment ID for final message
    deployment_id = deployment_data.get("deployment_id", "N/A")

    # Define cleanup steps
    steps = [
        DeploymentStep("Connect to Juju controller"),
        DeploymentStep("Destroy model"),
        DeploymentStep("Cleanup complete"),
    ]

    # Create final success message for the panel
    final_success_message = f"""✅ [bold green]Charmed HPC cleanup completed successfully![/bold green]

[bold]Cleanup Summary:[/bold]
• Deployment ID: [cyan]{deployment_id}[/cyan]
• Model '{model_name}' destroyed
• Storage cleaned up
• Controller disconnected

[bold]Next Steps:[/bold]
• Verify removal: [cyan]juju models[/cyan]
• Check controller status: [cyan]juju controllers[/cyan]
• Deploy new cluster: [cyan]vantage deployment slurm-juju-localhost deploy <cluster-name>[/cyan]"""

    try:
        with deployment_progress_panel(
            steps=steps,
            console=console,
            verbose=False,  # Always use panel mode for clean display
            title="Cleaning up Charmed HPC Deployment",
            panel_title="🧹 Charmed HPC Cleanup Progress",
            final_message=final_success_message,
        ) as advance_step:
            advance_step("Connect to Juju controller", "starting")
            with SuppressOutput():
                await controller.connect()
            advance_step("Connect to Juju controller", "completed")

            advance_step("Destroy model", "starting")
            with SuppressOutput():
                await controller.destroy_model(model_name, destroy_storage=True)
            advance_step("Destroy model", "completed")

            advance_step("Cleanup complete", "starting")

            # Small pause to show the "starting" state
            import time

            time.sleep(1)

            advance_step("Cleanup complete", "completed", show_final=True)

            # Extended pause to allow users to read the final message in the panel
            time.sleep(8)  # 8 seconds to read the success message

    except Exception:
        raise
    finally:
        try:
            with SuppressOutput():
                await controller.disconnect()
        except Exception:
            pass  # Ignore disconnect errors
