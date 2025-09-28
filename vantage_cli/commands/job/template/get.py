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
"""Get job template command."""

from typing import Annotated

import typer
from rich import print_json
from rich.table import Table

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.commands.job.client import job_rest_client


@handle_abort
@attach_settings
async def get_job_template(
    ctx: typer.Context,
    template_id: Annotated[str, typer.Argument(help="ID or identifier of the job template to retrieve")],
):
    """Get details of a specific job template."""
    # Create REST API client
    client = job_rest_client(ctx.obj.profile, ctx.obj.settings)
    
    response = await client.get(f"/job-script-templates/{template_id}")
    template_data = response
    
    if ctx.obj.json_output:
        print_json(data=template_data)
    else:
        ctx.obj.console.print(f"📋 Job Template Details", style="bold magenta")
        ctx.obj.console.print()
        
        # Basic info table
        info_table = Table(show_header=False, box=None, padding=(0, 2))
        info_table.add_column("Field", style="cyan", min_width=15)
        info_table.add_column("Value", style="white")
        
        info_table.add_row("ID", str(template_data.get("id", "N/A")))
        info_table.add_row("Name", template_data.get("name", "N/A"))
        info_table.add_row("Identifier", template_data.get("identifier", "N/A"))
        info_table.add_row("Owner", template_data.get("owner_email", "N/A"))
        info_table.add_row("Description", template_data.get("description", "N/A"))
        info_table.add_row("Created", template_data.get("created_at", "N/A"))
        info_table.add_row("Updated", template_data.get("updated_at", "N/A"))
        info_table.add_row("Archived", "Yes" if template_data.get("is_archived", False) else "No")
        
        if template_data.get("cloned_from_id"):
            info_table.add_row("Cloned From", str(template_data.get("cloned_from_id")))
        
        ctx.obj.console.print(info_table)
        
        # Template Variables
        template_vars = template_data.get("template_vars")
        if template_vars:
            ctx.obj.console.print("\n� Template Variables:", style="bold green")
            vars_table = Table(show_header=True, header_style="bold cyan")
            vars_table.add_column("Variable", style="yellow")
            vars_table.add_column("Value", style="white")
            
            for key, value in template_vars.items():
                vars_table.add_row(str(key), str(value))
            
            ctx.obj.console.print(vars_table)
        
        # Template Files
        template_files = template_data.get("template_files")
        if template_files:
            ctx.obj.console.print("\n📁 Template Files:", style="bold blue")
            files_table = Table(show_header=True, header_style="bold cyan")
            files_table.add_column("Filename", style="green")
            files_table.add_column("Type", style="yellow")
            files_table.add_column("Created", style="dim")
            
            for file_info in template_files:
                files_table.add_row(
                    file_info.get("filename", "N/A"),
                    file_info.get("file_type", "N/A"),
                    file_info.get("created_at", "N/A")[:10] if file_info.get("created_at") else "N/A",
                )
            
            ctx.obj.console.print(files_table)
        
        # Workflow Files
        workflow_files = template_data.get("workflow_files")
        if workflow_files:
            ctx.obj.console.print("\n⚙️ Workflow Files:", style="bold purple")
            workflow_table = Table(show_header=True, header_style="bold cyan")
            workflow_table.add_column("Filename", style="green")
            workflow_table.add_column("Created", style="dim")
            
            for workflow_info in workflow_files:
                workflow_table.add_row(
                    workflow_info.get("filename", "N/A"),
                    workflow_info.get("created_at", "N/A")[:10] if workflow_info.get("created_at") else "N/A",
                )
            
            ctx.obj.console.print(workflow_table)
