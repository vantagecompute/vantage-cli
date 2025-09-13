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
