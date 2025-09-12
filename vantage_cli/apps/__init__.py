# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Applications management commands for Vantage CLI."""

from vantage_cli import AsyncTyper
from vantage_cli.commands.app.deploy import deploy_app
from vantage_cli.commands.app.list import list_apps

# Create the apps command group
apps_app = AsyncTyper(
    name="app",
    help="Deploy and manage applications on Vantage compute clusters.",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Register commands
apps_app.command("list")(list_apps)
apps_app.command("deploy")(deploy_app)
