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
"""Utility functions for SLURM LXD localhost deployments."""

import asyncio
import os
import shutil
import sys
from io import StringIO
from typing import Any, Dict

import snick
from juju.controller import Controller
from juju.errors import JujuError

from vantage_cli.exceptions import Abort


class SuppressOutput:
    """Context manager to suppress stdout and stderr output during operations."""

    def __enter__(self):
        """Enter the context and redirect output streams."""
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        # Also suppress any file descriptor output
        self._original_stdout_fd = None
        self._original_stderr_fd = None

        # Redirect stdout and stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()

        # Also try to suppress file descriptor output
        try:
            self._original_stdout_fd = os.dup(1)
            self._original_stderr_fd = os.dup(2)
            # Redirect file descriptors to /dev/null
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, 1)
            os.dup2(devnull, 2)
            os.close(devnull)
        except (OSError, AttributeError):
            # If file descriptor redirection fails, just continue with stdout/stderr redirection
            pass

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and restore original output streams."""
        # Restore stdout and stderr
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr

        # Restore file descriptors if they were redirected
        if self._original_stdout_fd is not None:
            try:
                os.dup2(self._original_stdout_fd, 1)
                os.close(self._original_stdout_fd)
            except OSError:
                pass
        if self._original_stderr_fd is not None:
            try:
                os.dup2(self._original_stderr_fd, 2)
                os.close(self._original_stderr_fd)
            except OSError:
                pass


def check_juju_available() -> None:
    """Check if Juju is available and provide installation instructions if not.

    Raises:
        Abort: If Juju is not found, with installation instructions
    """
    if not shutil.which("juju"):
        message = snick.dedent(
            """
            • Juju not found. Please install Juju first.

            • To install Juju, run the following command:
              sudo snap install juju --channel=3.6/stable

            • Or visit https://juju.is/docs/juju/install-juju for other installation methods.
            """
        ).strip()

        raise Abort(
            message,
            subject="Juju Required",
            log_message="Juju binary not found",
        )


async def is_ready(cluster_data: Dict[str, Any]) -> bool:
    """Check if the Juju localhost cluster is ready and reachable.

    This function checks if:
    1. The Juju model exists
    2. The Juju controller is accessible
    3. Key applications are running (slurmctld, slurmd, jupyterhub)

    Args:
        cluster_data: Dictionary containing cluster information including deployment_name

    Returns:
        True if cluster is ready and reachable, False otherwise
    """
    model_name = cluster_data.get("deployment_name")
    if not model_name:
        # Try to derive from cluster name
        cluster_name = cluster_data.get("name")
        if not cluster_name:
            return False
        # Common pattern: app-name-cluster-name-<uuid>
        # For checking, we need the actual model name which should be in deployment_name
        return False

    controller = Controller()

    try:
        # Try to connect to the controller
        with SuppressOutput():
            await asyncio.wait_for(controller.connect(), timeout=5.0)

        # Try to connect to the model
        with SuppressOutput():
            model = await asyncio.wait_for(controller.get_model(model_name), timeout=5.0)

        try:
            # Check if critical applications exist and are active
            with SuppressOutput():
                status = await asyncio.wait_for(model.get_status(), timeout=10.0)

            # Check for critical applications
            required_apps = [
                "slurmctld",
                "sackd",
                "slurmd",
                "vantage-jupyterhub",
                "mysql",
                "influxdb",
                "vantage-agent",
                "vantage-jupyterhub-nfs-client",
                "jobbergate-agent",
                "apptainer",
            ]
            apps = status.applications

            if not all(app in apps for app in required_apps):
                return False

            # Check if applications have units and they're active
            for app_name in required_apps:
                app = apps.get(app_name)
                if not app or not app.units:
                    return False

                # Check if at least one unit is active
                has_active_unit = False
                for unit in app.units.values():
                    workload_status = getattr(unit, "workload_status", None)
                    if workload_status == "active":
                        has_active_unit = True
                        break

                if not has_active_unit:
                    return False

            return True

        finally:
            with SuppressOutput():
                await model.disconnect()

    except (asyncio.TimeoutError, JujuError, Exception):
        return False
    finally:
        try:
            with SuppressOutput():
                await controller.disconnect()
        except Exception:
            pass
