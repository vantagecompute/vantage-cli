# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""License management commands for Vantage CLI."""

from vantage_cli import AsyncTyper

from .configuration import configuration_app
from .deployment import deployment_app
from .product import product_app
from .server import server_app

# Create the license command group
license_app = AsyncTyper(
    name="license",
    help="Manage software licenses, license servers, and licensing configurations.",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Register subcommands
license_app.add_typer(server_app, name="server")
license_app.add_typer(product_app, name="product")
license_app.add_typer(configuration_app, name="configuration")
license_app.add_typer(deployment_app, name="deployment")
