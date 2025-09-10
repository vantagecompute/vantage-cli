# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
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
