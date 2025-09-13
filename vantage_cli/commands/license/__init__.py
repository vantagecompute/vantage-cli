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
