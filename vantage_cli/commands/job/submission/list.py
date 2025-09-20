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
"""List job submissions command."""

import typer
from rich import print_json

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import RenderStepOutput


@handle_abort
@attach_settings
async def list_job_submissions(ctx: typer.Context):
    """List all job submissions."""
    json_output = getattr(ctx.obj, "json_output", False)

    # Get command start time for timing
    command_start_time = getattr(ctx.obj, "command_start_time", None) if ctx.obj else None

    renderer = RenderStepOutput(
        console=ctx.obj.console,
        operation_name="List Job Submissions",
        step_names=["Fetching job submissions", "Formatting output"],
        verbose=True,
        command_start_time=command_start_time,
    )

    with renderer:
        # Mock data fetch
        submissions = [
            {"submission_id": "sub-12345", "script": "example1.sh", "status": "running"},
            {"submission_id": "sub-67890", "script": "example2.sh", "status": "completed"},
        ]

        renderer.complete_step("Fetching job submissions")

        renderer.start_step("Formatting output")

        if json_output:
            print_json(data={"submissions": submissions})
        else:
            ctx.obj.console.print("📋 Job submissions:")
            for sub in submissions:
                ctx.obj.console.print(
                    f"  {sub['submission_id']} - {sub['script']} ({sub['status']})"
                )

        renderer.complete_step("Formatting output")
