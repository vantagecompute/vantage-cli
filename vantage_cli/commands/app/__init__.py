# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Application deployment commands for Vantage CLI."""

from vantage_cli import AsyncTyper

from .deploy import deploy_app
from .list import list_apps

# Create the apps command group
apps_app = AsyncTyper(
    name="apps",
    help="Deploy and manage applications on Vantage compute clusters.",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Register subcommands directly
apps_app.command("list")(list_apps)
apps_app.command("deploy")(deploy_app)

# Add plural alias for list command
apps_app.command("apps", help="List all applications (alias for 'list')")(list_apps)

__all__ = ["apps_app"]
