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
