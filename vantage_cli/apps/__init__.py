# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Cluster management commands for Vantage CLI."""

from vantage_cli import AsyncTyper
from vantage_cli.apps.juju_localhost import juju_localhost_app
from vantage_cli.apps.multipass_singlenode import multipass_singlenode_app

# Create the apps command group
apps_app = AsyncTyper(
    name="apps",
    help="Vantage infrastructure automation applications.",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Register subcommand groups
apps_app.add_typer(juju_localhost_app)
apps_app.add_typer(multipass_singlenode_app)
