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
"""Cloud management commands package."""

from pathlib import Path

from vantage_cli import AsyncTyper

from .credential import credential_app
from .credential.list import list_command as list_credentials_command
from .get import get_command
from .list import list_command

cloud_app = AsyncTyper(
    name="cloud",
    help="Manage cloud provider configurations.",
    no_args_is_help=True,
)

# Register cloud commands
cloud_app.command("get")(get_command)
cloud_app.command("list")(list_command)

# Add credential subcommand group
cloud_app.add_typer(credential_app)

# Add credentials as an alias for "credential list"
cloud_app.command("credentials", hidden=True)(list_credentials_command)


# Dynamically register cloud provider commands
def _register_cloud_provider_commands():
    """Register all cloud provider apps as subcommands."""
    import importlib

    # Get the clouds directory
    clouds_dir = Path(__file__).parent.parent.parent / "clouds"

    if not clouds_dir.exists():
        return

    # Iterate through cloud provider directories
    for cloud_dir in clouds_dir.iterdir():
        if not cloud_dir.is_dir() or cloud_dir.name.startswith("__"):
            continue

        # Check if main.py exists and has an 'app' attribute
        main_file = cloud_dir / "main.py"
        if not main_file.exists():
            continue

        try:
            # Import the cloud provider's main module
            module_name = f"vantage_cli.clouds.{cloud_dir.name}.main"
            cloud_module = importlib.import_module(module_name)

            # Check if the module has an 'app' attribute (typer app)
            if hasattr(cloud_module, "app"):
                cloud_typer_app = getattr(cloud_module, "app")
                # Use hyphenated name instead of underscore
                cloud_name = cloud_dir.name.replace("_", "-")
                # Register it as a subcommand
                cloud_app.add_typer(cloud_typer_app, name=cloud_name)
        except Exception:
            # Silently skip clouds that don't have proper app structure
            pass


# Register cloud provider commands when this module is imported
_register_cloud_provider_commands()
