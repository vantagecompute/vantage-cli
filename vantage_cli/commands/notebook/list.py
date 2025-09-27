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
"""List notebooks command."""

import logging
from typing import Optional

import typer
from typing_extensions import Annotated

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.sdk.notebook.crud import notebook_sdk

logger = logging.getLogger(__name__)


@handle_abort
@attach_settings
async def list_notebooks(
    ctx: typer.Context,
    cluster: Annotated[
        Optional[str], typer.Option("--cluster", "-c", help="Filter by cluster name")
    ] = None,
    status: Annotated[
        Optional[str], typer.Option("--status", "-s", help="Filter by notebook status")
    ] = None,
    kernel: Annotated[
        Optional[str], typer.Option("--kernel", "-k", help="Filter by kernel type")
    ] = None,
    limit: Annotated[
        Optional[int], typer.Option("--limit", "-l", help="Maximum number of notebooks to return")
    ] = None,
):
    """List notebook servers."""
    # Use UniversalOutputFormatter for consistent output

    try:
        # Use the SDK to get notebooks
        logger.debug("Using SDK to list notebooks")
        notebooks = await notebook_sdk.list_notebooks(ctx, cluster=cluster, limit=limit)

        if not notebooks:
            ctx.obj.formatter.render_list(
                data=[],
                resource_name="Notebook Servers",
                empty_message="No notebook servers found.",
            )
            return

        # Convert Notebook objects to dict format for the formatter
        notebooks_data = []
        for notebook in notebooks:
            notebook_dict = {
                "id": notebook.id,
                "name": notebook.name,
                "cluster_name": notebook.cluster_name,
                "partition": notebook.partition,
                "owner": notebook.owner,
                "server_url": notebook.server_url,
                "slurm_job_id": notebook.slurm_job_id,
                "created_at": notebook.created_at,
            }
            notebooks_data.append(notebook_dict)

        # Use formatter to render the notebooks list
        ctx.obj.formatter.render_list(
            data=notebooks_data,
            resource_name="Notebook Servers",
            empty_message="No notebook servers found.",
        )

    except Abort:
        # Re-raise Abort exceptions as they contain user-friendly messages
        raise
    except Exception as e:
        logger.error(f"Unexpected error listing notebooks: {e}")
        ctx.obj.formatter.render_error(
            error_message="An unexpected error occurred while listing notebook servers.",
            details={"error": str(e)},
        )
