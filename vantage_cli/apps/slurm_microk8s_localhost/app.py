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
"""MicroK8s application support for deploying the Slurm Operator & Slurm cluster.

Implements the manual steps documented in the local README:

1. Enable required MicroK8s addons (hostpath-storage, dns, metallb)
2. Add Helm repositories (jetstack, prometheus-community)
3. Install cert-manager, Prometheus stack, Slurm Operator CRDs
4. Download values files & install Slurm Operator
5. Install a Slurm cluster release

Notes:
- These steps are inherently idempotent; failures on already-installed/ enabled
  components are treated as warnings (not fatal) when safe.
- This command invokes system binaries (sudo microk8s.* & curl). The user must
  have the appropriate privileges. We intentionally keep the logic simple and
  transparent; advanced lifecycle management belongs in a dedicated orchestrator.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

import typer
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from typing_extensions import Annotated

from vantage_cli.apps.common import (
    validate_client_credentials,
    validate_cluster_data,
)
from vantage_cli.config import attach_settings

DEFAULT_METALLB_RANGE = "10.64.140.43-10.64.140.49"
SLURM_OPERATOR_VERSION = "0.4.0"
SLURM_OPERATOR_REPO_BASE = (
    "https://raw.githubusercontent.com/SlinkyProject/slurm-operator/refs/tags"
)


def _run(
    cmd: list[str],
    console: Console,
    *,
    check: bool = True,
    allow_fail: bool = False,
    env: Optional[dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """Run a shell command (no shell=True) and optionally allow failure.

    Args:
        cmd: Command & arguments
        console: Rich console for user feedback
        check: If True raise on non‑zero exit unless allow_fail
        allow_fail: If True convert non‑zero exit into warning
        env: Optional environment overrides
    """
    console.print(f"[dim]$ {' '.join(cmd)}[/dim]")
    try:
        cp = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env or os.environ.copy(),
            check=False,
        )
    except FileNotFoundError:
        console.print(f"[red]Command not found: {cmd[0]}[/red]")
        if check and not allow_fail:
            raise typer.Exit(code=1)
        return subprocess.CompletedProcess(cmd, 127, "")

    if cp.returncode != 0 and check and not allow_fail:
        console.print(f"[red]Command failed (exit {cp.returncode}): {' '.join(cmd)}[/red]")
        console.print(cp.stdout)
        raise typer.Exit(code=cp.returncode)

    if cp.returncode != 0 and allow_fail:
        console.print(
            f"[yellow]Warning: command returned {cp.returncode} (continuing): {' '.join(cmd)}[/yellow]"
        )
        logger.warning(
            f"Non‑fatal command failure: {' '.join(cmd)} -> {cp.returncode}\n{cp.stdout}"
        )
    return cp


async def deploy(
    ctx: typer.Context,
    cluster_data: Optional[Dict[str, Any]] = None,
    *,
    metallb_range: str = DEFAULT_METALLB_RANGE,
) -> None:
    """Deploy Slurm Operator & Slurm cluster onto MicroK8s.

    This will perform a sequence of imperative steps. It aims for a *best effort*
    deployment suitable for local development / experimentation—not production.
    """
    console = Console()
    console.print(Panel("Slurm Operator on MicroK8s"))
    console.print("Deploying slurm-operator & slurm cluster on MicroK8s...")

    microk8s_bin = shutil.which("microk8s")
    if not microk8s_bin:
        console.print(
            "[red]microk8s binary not found in PATH. Please install microk8s first.[/red]"
        )
        raise typer.Exit(code=1)

    # Validate cluster data & surface credentials (even if not strictly needed yet)
    if cluster_data:
        cluster_data = validate_cluster_data(cluster_data, console)
        validate_client_credentials(cluster_data, console)

    # 1. Wait for microk8s to be ready
    _run(["sudo", microk8s_bin, "status", "--wait-ready"], console, allow_fail=False)

    # 2. Enable core addons (idempotent; allow failures for already enabled)
    _run(["sudo", microk8s_bin, "enable", "hostpath-storage"], console, allow_fail=True)
    _run(["sudo", microk8s_bin, "enable", "dns"], console, allow_fail=True)
    _run(["sudo", microk8s_bin, "enable", f"metallb:{metallb_range}"], console, allow_fail=True)

    # 3. Helm repositories (microk8s embeds helm3 as 'microk8s.helm')
    helm_cmd = shutil.which("microk8s.helm") or "microk8s.helm"
    _run(
        ["sudo", helm_cmd, "repo", "add", "jetstack", "https://charts.jetstack.io"],
        console,
        allow_fail=True,
    )
    _run(
        [
            "sudo",
            helm_cmd,
            "repo",
            "add",
            "prometheus-community",
            "https://prometheus-community.github.io/helm-charts",
        ],
        console,
        allow_fail=True,
    )
    _run(["sudo", helm_cmd, "repo", "update"], console, allow_fail=True)

    # 4. Install cert-manager (CRDs handled by chart flags)
    _run(
        [
            "sudo",
            helm_cmd,
            "install",
            "cert-manager",
            "jetstack/cert-manager",
            "--namespace",
            "cert-manager",
            "--create-namespace",
            "--set",
            "installCRDs=true",
        ],
        console,
        allow_fail=True,
    )

    # 5. Install Prometheus stack for metrics
    _run(
        [
            "sudo",
            helm_cmd,
            "install",
            "prometheus",
            "prometheus-community/kube-prometheus-stack",
            "--namespace",
            "prometheus",
            "--create-namespace",
        ],
        console,
        allow_fail=True,
    )

    # 6. Install Slurm Operator CRDs
    _run(
        [
            "sudo",
            helm_cmd,
            "install",
            "slurm-operator-crds",
            "oci://ghcr.io/slinkyproject/charts/slurm-operator-crds",
        ],
        console,
        allow_fail=True,
    )

    # 7. Download operator & slurm values (so user can inspect / tweak) then install
    work_dir = Path.cwd() / "microk8s-slurm"
    work_dir.mkdir(exist_ok=True)
    operator_values = work_dir / "values-operator.yaml"
    slurm_values = work_dir / "values-slurm.yaml"

    operator_values_url = (
        f"{SLURM_OPERATOR_REPO_BASE}/v{SLURM_OPERATOR_VERSION}/helm/slurm-operator/values.yaml"
    )
    slurm_values_url = (
        f"{SLURM_OPERATOR_REPO_BASE}/v{SLURM_OPERATOR_VERSION}/helm/slurm/values.yaml"
    )

    if not operator_values.exists():
        _run(
            ["curl", "-L", operator_values_url, "-o", str(operator_values)],
            console,
            allow_fail=False,
        )
    else:
        console.print(f"[green]Using existing {operator_values}[/green]")
    if not slurm_values.exists():
        _run(["curl", "-L", slurm_values_url, "-o", str(slurm_values)], console, allow_fail=False)
    else:
        console.print(f"[green]Using existing {slurm_values}[/green]")

    _run(
        [
            "sudo",
            helm_cmd,
            "install",
            "slurm-operator",
            "oci://ghcr.io/slinkyproject/charts/slurm-operator",
            f"--values={operator_values}",
            f"--version={SLURM_OPERATOR_VERSION}",
            "--namespace",
            "slinky",
            "--create-namespace",
        ],
        console,
        allow_fail=True,
    )

    # 8. Install Slurm cluster
    _run(
        [
            "sudo",
            helm_cmd,
            "install",
            "slurm",
            "oci://ghcr.io/slinkyproject/charts/slurm",
            f"--values={slurm_values}",
            f"--version={SLURM_OPERATOR_VERSION}",
            "--namespace",
            "slurm",
            "--create-namespace",
        ],
        console,
        allow_fail=True,
    )

    console.print(
        "[green]Deployment steps executed. Pods may take a few minutes to become ready.[/green]"
    )
    console.print("Check status with: sudo microk8s.kubectl get pods -A | grep -E 'slinky|slurm'")


@attach_settings
async def deploy_command(
    ctx: typer.Context,
    cluster_name: Annotated[
        Optional[str],
        typer.Option(
            "--cluster-name",
            help="Existing cluster name to fetch credentials (optional)",
        ),
    ] = None,
    metallb_range: Annotated[
        str,
        typer.Option(
            "--metallb-range",
            help="Address range to configure for MetalLB (start-end)",
            show_default=True,
        ),
    ] = DEFAULT_METALLB_RANGE,
) -> None:
    """CLI entrypoint for deploying MicroK8s Slurm stack."""
    cluster_data = None
    if cluster_name:
        try:
            from vantage_cli.commands.cluster import (
                utils as cluster_utils,  # local import to avoid cycles
            )

            cluster_data = await cluster_utils.get_cluster_by_name(
                ctx=ctx, cluster_name=cluster_name
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Could not retrieve cluster '{cluster_name}': {e}")
    await deploy(ctx=ctx, cluster_data=cluster_data, metallb_range=metallb_range)


__all__ = ["deploy", "deploy_command"]
