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

import logging
from typing import Any, Dict, Optional

import typer
from typing_extensions import Annotated

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.sdk.notebook.crud import notebook_sdk

logger = logging.getLogger(__name__)


def _get_username_from_persona(persona: Any, provided_username: Optional[str]) -> str:
    """Extract username from persona or use provided username.

    Args:
        persona: The persona object with identity data
        provided_username: Username provided by user (if any)

    Returns:
        Username to use for notebook creation

    Raises:
        Abort: If username cannot be determined
    """
    if provided_username:
        return provided_username

    if persona and persona.identity_data and persona.identity_data.email:
        user, domain = persona.identity_data.email.split("@")
        username_to_use = f"{user}_{domain.replace('.', '')}"
        logger.debug(f"Using username from authenticated user: {username_to_use}")
        return username_to_use

    raise Abort(
        "Could not determine username. Please provide --username option.",
        subject="Username Required",
        log_message="Missing persona email for username derivation",
    )


def _build_server_options(
    partition: str,
    cpu_cores: Optional[int],
    memory: Optional[str],
    gpus: Optional[int],
    node: Optional[str],
) -> Dict[str, Any]:
    """Build server options dictionary from resource specifications.

    Args:
        partition: SLURM partition
        cpu_cores: Number of CPU cores
        memory: Memory specification
        gpus: Number of GPUs
        node: Specific node name

    Returns:
        Dictionary of server options
    """
    server_options: Dict[str, Any] = {"partition": partition}

    if cpu_cores:
        server_options["cpu_cores"] = cpu_cores
    if memory:
        server_options["memory"] = memory
    if gpus:
        server_options["gpus"] = gpus
    if node:
        server_options["node"] = node

    return server_options


def _build_result_data(
    result: Dict[str, Any],
    username: str,
    server_name: str,
    partition: str,
    server_options: Dict[str, Any],
    persona: Any,
) -> Dict[str, Any]:
    """Build formatted result data for display.

    Args:
        result: Result from notebook creation
        username: Username used
        server_name: Name of the server
        partition: SLURM partition
        server_options: Server resource options
        persona: User persona

    Returns:
        Formatted result data dictionary
    """
    result_data: Dict[str, Any] = {
        "cluster": result.get("cluster_name"),
        "username": result.get("username") or username,
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
    resources = {k: v for k, v in server_options.items() if k != "partition"}
    result_data["resources"] = {
        "partition": partition,
        **resources,
    }

    return result_data


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
    persona = getattr(ctx.obj, "persona", None)

    try:
        # Validate required parameters
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

        # Get username
        username_to_use = _get_username_from_persona(persona, username)

        # Build server options from resource specifications
        server_options = _build_server_options(partition, cpu_cores, memory, gpus, node)

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
        result_data = _build_result_data(
            result, username_to_use, server_name, partition, server_options, persona
        )

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
