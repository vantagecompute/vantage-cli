# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
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
