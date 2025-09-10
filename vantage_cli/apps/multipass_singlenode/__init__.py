"""Multipass single-node deployment app package."""

from vantage_cli import AsyncTyper

from .app import deploy_command

multipass_singlenode_app = AsyncTyper(
    name="multipass-singlenode",
    help="Multipass single-node application commands.",
    invoke_without_command=True,
    no_args_is_help=True,
)

multipass_singlenode_app.command("deploy")(deploy_command)
