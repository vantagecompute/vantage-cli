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
"""Get notebook command."""

import logging

import typer
from typing_extensions import Annotated

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.sdk.notebook.crud import notebook_sdk

logger = logging.getLogger(__name__)


@handle_abort
@attach_settings
async def get_notebook(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Notebook server name")],
):
    """Get notebook server details."""
    # Use UniversalOutputFormatter for consistent output

    try:
        # Use SDK to get notebook
        logger.debug(f"Fetching notebook '{name}' from SDK")
        notebook = await notebook_sdk.get_notebook(ctx, name)

        if not notebook:
            ctx.obj.formatter.render_error(error_message=f"Notebook server '{name}' not found.")
            raise Abort(
                f"Notebook server '{name}' not found.",
                subject="Notebook Not Found",
                log_message=f"Notebook '{name}' not found",
            )

        # Convert Notebook object to dict format for the formatter
        notebook_data = {
            "id": notebook.id,
            "name": notebook.name,
            "cluster_name": notebook.cluster_name,
            "partition": notebook.partition,
            "owner": notebook.owner,
            "server_url": notebook.server_url,
            "slurm_job_id": notebook.slurm_job_id,
            "created_at": notebook.created_at,
            "updated_at": notebook.updated_at,
        }

        # Use formatter to render the notebook details
        ctx.obj.formatter.render_get(
            data=notebook_data, resource_name="Notebook Server", resource_id=name
        )

    except Abort:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting notebook '{name}': {e}")
        ctx.obj.formatter.render_error(
            error_message=f"An unexpected error occurred while getting notebook '{name}'.",
            details={"error": str(e)},
        )
