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
"""Job management commands for Vantage CLI."""

from vantage_cli import AsyncTyper

from .script import script_app
from .submission import job_submission_app
from .template import job_template_app

# Create the job command group
job_app = AsyncTyper(
    name="job",
    help="Manage computational jobs, scripts, submissions, and job templates for HPC workloads.",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Register subcommands
job_app.add_typer(script_app, name="script")
job_app.add_typer(job_submission_app, name="submission")
job_app.add_typer(job_template_app, name="template")
