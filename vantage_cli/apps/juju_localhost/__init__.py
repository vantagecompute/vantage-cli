"""Juju localhost deployment app package."""

from vantage_cli import AsyncTyper

from .app import deploy_command

juju_localhost_app = AsyncTyper(
    name="juju-localhost",
    help="Juju localhost SLURM application commands.",
    invoke_without_command=True,
    no_args_is_help=True,
)

juju_localhost_app.command("deploy")(deploy_command)
