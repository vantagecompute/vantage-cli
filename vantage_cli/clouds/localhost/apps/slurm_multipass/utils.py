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
"""Utility functions for SLURM on Multipass localhost deployments."""

import json
import shutil
import subprocess
from shutil import which
from typing import Any, Dict

import snick

from vantage_cli.exceptions import Abort


def check_multipass_available() -> None:
    """Check if Multipass is available and provide installation instructions if not.

    Raises:
        Abort: If Multipass is not found, with installation instructions
    """
    if not shutil.which("multipass"):
        message = snick.dedent(
            """
            • Multipass not found. Please install Multipass first.

            • To install Multipass, run the following command:
              sudo snap install multipass

            • Or visit https://multipass.run/install for other installation methods.
            """
        ).strip()

        raise Abort(
            message,
            subject="Multipass Required",
            log_message="Multipass binary not found",
        )


def is_ready(cluster_data: Dict[str, Any]) -> bool:
    """Check if the Multipass localhost cluster is ready and reachable.

    This function checks if:
    1. Multipass CLI is available
    2. The VM instance exists
    3. The VM is running
    4. SLURM services are accessible in the VM

    Args:
        cluster_data: Dictionary containing cluster information including deployment_name

    Returns:
        True if cluster is ready and reachable, False otherwise
    """
    # Get the instance name from deployment_name
    instance_name = cluster_data.get("deployment_name")
    if not instance_name:
        # Try fallback to old pattern
        client_id = cluster_data.get("client_id")
        if client_id:
            instance_name = f"vantage-multipass-singlenode-{client_id.split('-')[0]}"
        else:
            return False

    # Check if multipass is available
    multipass = which("multipass")
    if not multipass:
        return False

    try:
        # Check if instance exists and get its state
        result = subprocess.run(
            ["multipass", "list", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return False

        instances_data = json.loads(result.stdout)
        instances = instances_data.get("list", [])

        # Find our instance
        instance = None
        for inst in instances:
            if inst.get("name") == instance_name:
                instance = inst
                break

        if not instance:
            return False

        # Check if instance is running
        state = instance.get("state", "").lower()
        if state != "running":
            return False

        # Check if SLURM services are accessible by running a simple slurm command
        result = subprocess.run(
            ["multipass", "exec", instance_name, "--", "systemctl", "is-active", "slurmd"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # If slurmd service is active, consider cluster ready
        if result.returncode == 0 and result.stdout.strip() == "active":
            return True

        return False

    except (
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
        json.JSONDecodeError,
        Exception,
    ):
        return False
