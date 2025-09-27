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

from .booking import app as booking_app
from .booking.list import list_bookings
from .configuration import configuration_app
from .configuration.list import list_license_configurations
from .deployment import deployment_app
from .deployment.list import list_license_deployments
from .feature import feature_app
from .feature.list import list_license_features
from .product import product_app
from .product.list import list_license_products
from .server import server_app
from .server.list import list_license_servers

# Create the license command group
license_app = AsyncTyper(
    name="license",
    help="Manage software licenses, license servers, and licensing configurations.",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Register subcommands
license_app.add_typer(booking_app, name="booking")
license_app.add_typer(server_app, name="server")
license_app.add_typer(product_app, name="product")
license_app.add_typer(configuration_app, name="configuration")
license_app.add_typer(deployment_app, name="deployment")
license_app.add_typer(feature_app, name="feature")

# Add plural aliases that directly call the list commands (hidden from help)
license_app.command("bookings", hidden=True)(list_bookings)
license_app.command("servers", hidden=True)(list_license_servers)
license_app.command("products", hidden=True)(list_license_products)
license_app.command("configurations", hidden=True)(list_license_configurations)
license_app.command("deployments", hidden=True)(list_license_deployments)
license_app.command("features", hidden=True)(list_license_features)
