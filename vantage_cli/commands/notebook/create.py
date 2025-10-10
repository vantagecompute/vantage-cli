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

from typing import Any, Dict, Optional

import typer
from loguru import logger
from typing_extensions import Annotated

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.sdk.notebook.crud import notebook_sdk


@handle_abort
@attach_settings
@attach_persona
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

    persona = getattr(ctx.obj, "persona", None)

    try:
        # Get username from token if not provided
        if username is None:
            # Extract username from the authenticated user's email
            if persona and persona.identity_data and persona.identity_data.email:
                username_to_use = persona.identity_data.email.split("@")[0]
                logger.debug(f"Using username from authenticated user: {username_to_use}")
            else:
                raise Abort(
                    "Could not determine username. Please provide --username option.",
                    subject="Username Required",
                    log_message="Missing persona email for username derivation",
                )
        else:
            username_to_use = username

        if server_name is None:
            raise Abort(
                "Notebook creation now requires a server name. Provide one with --name.",
                subject="Server Name Required",
                log_message="Notebook create invoked without server_name",
            )

        if partition is None:
            raise Abort(
                "Notebook creation requires a partition. Provide one with --partition.",
                subject="Partition Required",
                log_message="Notebook create invoked without partition",
            )

        # Build server options from resource specifications
        server_options: Dict[str, Any] = {"partition": partition}

        if cpu_cores:
            server_options["cpu_cores"] = cpu_cores
        if memory:
            server_options["memory"] = memory
        if gpus:
            server_options["gpus"] = gpus
        if node:
            server_options["node"] = node

        # Use SDK to create notebook server via GraphQL
        logger.debug(
            f"Requesting notebook server '{server_name}' via GraphQL for user '{username_to_use}'"
        )
        result = await notebook_sdk.create_notebook(
            ctx=ctx,
            cluster_name=cluster_name,
            username=username_to_use,
            server_name=server_name,
            server_options=server_options,
        )

        # Format the result for display
        result_data: Dict[str, Any] = {
            "cluster": result.get("cluster_name"),
            "username": result.get("username") or username_to_use,
            "server_name": result.get("server_name"),
            "status": result.get("status"),
            "partition": result.get("partition"),
        }

        if result.get("server_url"):
            result_data["server_url"] = result["server_url"]
        if result.get("slurm_job_id"):
            result_data["slurm_job_id"] = result["slurm_job_id"]
        if persona and persona.identity_data and persona.identity_data.email:
            result_data.setdefault("owner_email", persona.identity_data.email)

        # Add resource specs if they were provided
        if server_options:
            result_data["resources"] = {k: v for k, v in server_options.items() if k != "partition"}

        # Include partition information separately for clarity
        result_data["resources"] = {
            "partition": partition,
            **(result_data.get("resources") or {}),
        }

        # Use formatter to render the created notebook
        ctx.obj.formatter.render_get(
            data=result_data,
            resource_name="Notebook Server",
            resource_id=result.get("server_name", server_name),
        )

        if not ctx.obj.json_output:
            status_msg = result.get("message", "Notebook server creation requested")
            ctx.obj.console.print(f"\n✅ {status_msg}", style="bold green")

    except Abort:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating notebook: {e}")
        ctx.obj.formatter.render_error(
            error_message="An unexpected error occurred while creating the notebook server.",
            details={"error": str(e)},
        )
