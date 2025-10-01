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
"""Create notebook command."""

from typing import Optional

import typer
from loguru import logger
from typing_extensions import Annotated

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.render import UniversalOutputFormatter
from vantage_cli.sdk.notebook.crud import notebook_sdk


@handle_abort
@attach_settings
async def create_notebook(
    ctx: typer.Context,
    cluster_name: Annotated[str, typer.Option("--cluster", "-c", help="Name of the cluster")],
    username: Annotated[
        Optional[str], typer.Option("--username", "-u", help="JupyterHub username")
    ] = None,
    server_name: Annotated[
        Optional[str], typer.Option("--name", "-n", help="Named server (optional)")
    ] = None,
    partition: Annotated[
        Optional[str], typer.Option("--partition", help="SLURM partition to use")
    ] = None,
    cpu_cores: Annotated[
        Optional[int], typer.Option("--cpu-cores", help="Number of CPU cores")
    ] = None,
    memory: Annotated[Optional[str], typer.Option("--mem", help="Memory (e.g., 4G, 8G)")] = None,
    gpus: Annotated[Optional[int], typer.Option("--gpu", help="Number of GPUs")] = None,
    node: Annotated[Optional[str], typer.Option("--node", help="Specific node to use")] = None,
):
    """Create a new Jupyter notebook server on a cluster.
    
    Creates a notebook server using JupyterHub API with resource specifications.
    If username is not provided, it will use the authenticated user's email.
    """
    # Use UniversalOutputFormatter for consistent output
    formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=ctx.obj.json_output)

    try:
        # Get username from token if not provided
        if not username:
            # Extract username from the authenticated user's email
            if hasattr(ctx.obj, "persona") and ctx.obj.persona:
                username = ctx.obj.persona.identity_data.email
                if username:
                    # Use email prefix as username
                    username = username.split("@")[0]
                    logger.debug(f"Using username from authenticated user: {username}")
                else:
                    raise Abort(
                        "Could not determine username. Please provide --username option.",
                        subject="Username Required",
                        log_message="No username provided and no email in persona",
                    )
            else:
                raise Abort(
                    "Could not determine username. Please provide --username option.",
                    subject="Username Required",
                    log_message="No persona data available",
                )

        # Build server options from resource specifications
        server_options = {}
        
        if partition:
            server_options["partition"] = partition
        if cpu_cores:
            server_options["cpu_cores"] = cpu_cores
        if memory:
            server_options["memory"] = memory
        if gpus:
            server_options["gpus"] = gpus
        if node:
            server_options["node"] = node

        # Use SDK to create notebook server
        logger.debug(
            f"Creating notebook server for user '{username}' on cluster '{cluster_name}'"
        )
        result = await notebook_sdk.create_notebook(
            ctx=ctx,
            cluster_name=cluster_name,
            username=username,
            server_name=server_name,
            server_options=server_options if server_options else None,
        )

        # Format the result for display
        result_data = {
            "cluster": result.get("cluster_name"),
            "username": result.get("username"),
            "server_name": result.get("server_name"),
            "status": result.get("status"),
        }

        # Add resource specs if they were provided
        if server_options:
            result_data["resources"] = server_options

        # Use formatter to render the created notebook
        formatter.render_get(
            data=result_data,
            resource_name="Notebook Server",
            resource_id=result.get("server_name", "default"),
        )

        if not ctx.obj.json_output:
            status_msg = result.get("message", "Server created successfully")
            ctx.obj.console.print(f"\n✅ {status_msg}", style="bold green")

    except Abort:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating notebook: {e}")
        formatter.render_error(
            error_message="An unexpected error occurred while creating the notebook server.",
            details={"error": str(e)},
        )
