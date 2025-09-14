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
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort

console = Console()


@handle_abort
@attach_settings
async def get_job_submission(
    ctx: typer.Context,
    submission_id: Annotated[str, typer.Argument(help="ID of the job submission to retrieve")],
):
    """Get details of a specific job submission."""
    if get_effective_json_output(ctx):
        print_json(
            data={"submission_id": submission_id, "script": "example.sh", "status": "running"}
        )
    else:
        console.print(f"📋 Job submission details for {submission_id}")
        console.print("  Script: example.sh")
        console.print("  Status: running")
