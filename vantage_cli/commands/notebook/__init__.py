# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Notebook management commands for Vantage CLI."""

from vantage_cli import AsyncTyper

from .create import create_notebook
from .delete import delete_notebook
from .get import get_notebook
from .list import list_notebooks
from .update import update_notebook

# Create the notebook command group
notebook_app = AsyncTyper(
    name="notebook",
    help="Manage Jupyter notebooks and computational notebooks for data science and research.",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Register all commands
notebook_app.command("create")(create_notebook)
notebook_app.command("delete")(delete_notebook)
notebook_app.command("get")(get_notebook)
notebook_app.command("list")(list_notebooks)
notebook_app.command("update")(update_notebook)
