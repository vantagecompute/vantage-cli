"""Juju localhost deployment app package."""

from vantage_cli import AsyncTyper

from .app import deploy_command

juju_localhost_app = AsyncTyper(
    name="juju-localhost",
    help="Juju localhost SLURM application commands.",
    context_settings={
        "allow_extra_args": True,
        "allow_interspersed_args": True,
        "ignore_unknown_options": True,
    },
)

juju_localhost_app.command("deploy")(deploy_command)
