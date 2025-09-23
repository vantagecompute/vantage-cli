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

import shutil

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
