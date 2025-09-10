# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""License configuration management commands."""

from vantage_cli import AsyncTyper

from .create import create_license_configuration
from .delete import delete_license_configuration
from .get import get_license_configuration
from .list import list_license_configurations
from .update import update_license_configuration

# Create the license configuration command group
configuration_app = AsyncTyper(
    name="configuration",
    help="Manage license configurations and policy settings.",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Register all commands
configuration_app.command("create")(create_license_configuration)
configuration_app.command("delete")(delete_license_configuration)
configuration_app.command("get")(get_license_configuration)
configuration_app.command("list")(list_license_configurations)
configuration_app.command("update")(update_license_configuration)
