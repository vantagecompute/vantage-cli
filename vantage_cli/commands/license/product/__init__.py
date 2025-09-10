# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
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
