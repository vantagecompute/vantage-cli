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
"""Job submission management commands."""

from vantage_cli import AsyncTyper

from .create import create_job_submission
from .delete import delete_job_submission
from .get import get_job_submission
from .list import list_job_submissions
from .update import update_job_submission

job_submission_app = AsyncTyper(name="submission", help="Manage job submissions")

job_submission_app.command("create", help="Create a new job submission")(create_job_submission)
job_submission_app.command("delete", help="Delete a job submission")(delete_job_submission)
job_submission_app.command("get", help="Get details of a specific job submission")(
    get_job_submission
)
job_submission_app.command("list", help="List all job submissions")(list_job_submissions)
job_submission_app.command("update", help="Update a job submission")(update_job_submission)
