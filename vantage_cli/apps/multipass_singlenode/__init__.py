"""Multipass single-node deployment app package."""

from vantage_cli import AsyncTyper

from .app import deploy_command

multipass_singlenode_app = AsyncTyper(
    name="multipass-singlenode",
    help="Multipass single-node application commands.",
)

multipass_singlenode_app.command("deploy")(deploy_command)
