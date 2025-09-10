# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Job template management commands."""

from vantage_cli import AsyncTyper

from .create import create_job_template
from .delete import delete_job_template
from .get import get_job_template
from .list import list_job_templates
from .update import update_job_template

job_template_app = AsyncTyper(name="template", help="Manage job templates")

job_template_app.command("create", help="Create a new job template")(create_job_template)
job_template_app.command("delete", help="Delete a job template")(delete_job_template)
job_template_app.command("get", help="Get details of a specific job template")(get_job_template)
job_template_app.command("list", help="List all job templates")(list_job_templates)
job_template_app.command("update", help="Update a job template")(update_job_template)
