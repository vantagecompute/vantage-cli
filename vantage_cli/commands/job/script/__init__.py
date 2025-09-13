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
"""Job script management commands."""

from vantage_cli import AsyncTyper

from .create import create_job_script
from .delete import delete_job_script
from .get import get_job_script
from .list import list_job_scripts
from .update import update_job_script

# Create the job script command group
script_app = AsyncTyper(
    name="script",
    help="Manage job scripts for computational workloads and batch processing.",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Register all commands
script_app.command("create")(create_job_script)
script_app.command("delete")(delete_job_script)
script_app.command("get")(get_job_script)
script_app.command("list")(list_job_scripts)
script_app.command("update")(update_job_script)
