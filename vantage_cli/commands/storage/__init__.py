# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Storage management commands for Vantage CLI."""

from vantage_cli import AsyncTyper

from .attach import attach_storage
from .create import create_storage
from .delete import delete_storage
from .detach import detach_storage
from .get import get_storage
from .list import list_storage
from .update import update_storage

# Create the storage command group
storage_app = AsyncTyper(
    name="storage",
    help="Manage storage volumes, disks, and storage configurations for cloud infrastructure.",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Register all commands
storage_app.command("attach")(attach_storage)
storage_app.command("create")(create_storage)
storage_app.command("delete")(delete_storage)
storage_app.command("detach")(detach_storage)
storage_app.command("get")(get_storage)
storage_app.command("list")(list_storage)
storage_app.command("update")(update_storage)
