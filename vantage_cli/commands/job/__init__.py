# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
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
