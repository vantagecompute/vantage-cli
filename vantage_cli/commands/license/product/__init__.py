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
"""License product management commands."""

from vantage_cli import AsyncTyper

from .create import create_license_product
from .delete import delete_license_product
from .get import get_license_product
from .list import list_license_products
from .update import update_license_product

# Create the license product command group
product_app = AsyncTyper(
    name="product",
    help="Manage license products and software licensing definitions.",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Register all commands
product_app.command("create")(create_license_product)
product_app.command("delete")(delete_license_product)
product_app.command("get")(get_license_product)
product_app.command("list")(list_license_products)
product_app.command("update")(update_license_product)
