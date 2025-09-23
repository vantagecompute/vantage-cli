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
"""Utility functions for SLURM on Juju localhost deployments."""

import shutil

import snick

from vantage_cli.exceptions import Abort


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
              sudo snap install juju --channel=3.5/stable

            • Or visit https://juju.is/docs/juju/install-juju for other installation methods.
            """
        ).strip()

        raise Abort(
            message,
            subject="Juju Required",
            log_message="Juju binary not found",
        )
