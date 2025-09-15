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
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort

console = Console()


@handle_abort
@attach_settings
async def list_job_submissions(ctx: typer.Context):
    """List all job submissions."""
    if get_effective_json_output(ctx):
        print_json(
            data={
                "submissions": [
                    {"submission_id": "sub-12345", "script": "example1.sh", "status": "running"},
                    {"submission_id": "sub-67890", "script": "example2.sh", "status": "completed"},
                ]
            }
        )
    else:
        console.print("📋 Job submissions:")
        console.print("  sub-12345 - example1.sh (running)")
        console.print("  sub-67890 - example2.sh (completed)")
