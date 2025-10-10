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
"""The vantage-cli application for deploying slurm to microk8s on localhost."""

from vantage_cli import AsyncTyper

from .app import deploy_command

microk8s_app = AsyncTyper(
    name="microk8s",
    help="MicroK8s application commands.",
    invoke_without_command=True,
    no_args_is_help=True,
)

microk8s_app.command("deploy")(deploy_command)
