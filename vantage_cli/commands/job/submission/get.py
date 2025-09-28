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
"""Get job submission command."""

from typing import Annotated

import typer
from rich import print_json
from rich.table import Table

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.commands.job.client import job_rest_client


@handle_abort
@attach_settings
async def get_job_submission(
    ctx: typer.Context,
    submission_id: Annotated[int, typer.Argument(help="ID of the job submission to retrieve")],
):
    """Get details of a specific job submission."""
    # Create REST API client
    client = job_rest_client(ctx.obj.profile, ctx.obj.settings)
    
    response = await client.get(f"/job-submissions/{submission_id}")
    submission_data = response
    
    if ctx.obj.json_output:
        print_json(data=submission_data)
    else:
        ctx.obj.console.print(f"📋 Job Submission Details", style="bold magenta")
        ctx.obj.console.print()
        
        # Basic info table
        info_table = Table(show_header=False, box=None, padding=(0, 2))
        info_table.add_column("Field", style="cyan", min_width=20)
        info_table.add_column("Value", style="white")
        
        info_table.add_row("ID", str(submission_data.get("id", "N/A")))
        info_table.add_row("Name", submission_data.get("name", "N/A"))
        info_table.add_row("Owner", submission_data.get("owner_email", "N/A"))
        info_table.add_row("Description", submission_data.get("description", "N/A"))
        info_table.add_row("Status", submission_data.get("status", "N/A"))
        info_table.add_row("Client ID", submission_data.get("client_id", "N/A"))
        info_table.add_row("Execution Directory", submission_data.get("execution_directory", "N/A"))
        info_table.add_row("Created", submission_data.get("created_at", "N/A"))
        info_table.add_row("Updated", submission_data.get("updated_at", "N/A"))
        info_table.add_row("Archived", "Yes" if submission_data.get("is_archived", False) else "No")
        
        if submission_data.get("job_script_id"):
            info_table.add_row("Job Script ID", str(submission_data.get("job_script_id")))
        
        if submission_data.get("slurm_job_id"):
            info_table.add_row("SLURM Job ID", str(submission_data.get("slurm_job_id")))
            info_table.add_row("SLURM Job State", submission_data.get("slurm_job_state", "N/A"))
        
        if submission_data.get("cloned_from_id"):
            info_table.add_row("Cloned From", str(submission_data.get("cloned_from_id")))
        
        if submission_data.get("report_message"):
            info_table.add_row("Report Message", submission_data.get("report_message"))
        
        ctx.obj.console.print(info_table)
        
        # SBATCH Arguments
        sbatch_args = submission_data.get("sbatch_arguments")
        if sbatch_args:
            ctx.obj.console.print("\n⚙️ SBATCH Arguments:", style="bold green")
            for arg in sbatch_args:
                ctx.obj.console.print(f"  • {arg}")
        
        # SLURM Job Info
        slurm_info = submission_data.get("slurm_job_info")
        if slurm_info:
            ctx.obj.console.print("\n📄 SLURM Job Info:", style="bold blue")
            ctx.obj.console.print(slurm_info[:500] + "..." if len(slurm_info) > 500 else slurm_info)
