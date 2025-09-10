# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
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
