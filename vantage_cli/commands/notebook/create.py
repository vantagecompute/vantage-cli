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

from typing import Any, Dict, Optional, cast

import typer
from loguru import logger
from rich import print_json
from typing_extensions import Annotated

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.gql_client import create_async_graphql_client


@handle_abort
@attach_settings
async def create_notebook(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the notebook server")],
    cluster_name: Annotated[str, typer.Option("--cluster", "-c", help="Name of the cluster")],
    partition_name: Annotated[str, typer.Option("--partition", help="Name of the partition")],
    cpu_cores: Annotated[Optional[int], typer.Option("--cpu", help="Number of CPU cores")] = None,
    memory: Annotated[Optional[float], typer.Option("--memory", help="Memory in MB")] = None,
    gpus: Annotated[Optional[int], typer.Option("--gpus", help="Number of GPUs")] = None,
):
    """Create a new Jupyter notebook server."""
    # GraphQL mutation to create notebook
    mutation = """
    mutation CreateNotebookServer($input: CreateNotebookInput!) {
        createJupyterServer(createNotebookInput: $input) {
            ... on NotebookServer {
                id
                name
                clusterName
                partition
                owner
                serverUrl
                slurmJobId
                createdAt
                updatedAt
            }
            ... on ClusterNotFound {
                message
            }
            ... on NotebookServerAlreadyExists {
                message
            }
            ... on PartitionNotFound {
                message
            }
        }
    }
    """

    # Build input variables
    variables: Dict[str, Any] = {
        "input": {
            "name": name,
            "clusterName": cluster_name,
            "partitionName": partition_name,
        }
    }

    # Add optional parameters if provided
    if cpu_cores is not None:
        variables["input"]["cpuCores"] = cpu_cores
    if memory is not None:
        variables["input"]["memory"] = memory
        variables["input"]["memoryUnit"] = "M"  # Assuming MB
    if gpus is not None:
        variables["input"]["gpus"] = gpus

    try:
        # Create async GraphQL client
        profile = getattr(ctx.obj, "profile", "default")
        graphql_client = create_async_graphql_client(ctx.obj.settings, profile)

        # Execute the mutation
        logger.debug("Creating notebook server")
        response_data = await graphql_client.execute_async(mutation, variables)

        result = response_data.get("createJupyterServer")

        if not result:
            Abort.require_condition(False, "No response from server")

        # Ensure result is a dictionary
        if not isinstance(result, dict):
            Abort.require_condition(False, "Invalid response format from server")

        # Type the result as a dictionary to help type checker
        result_dict = cast(Dict[str, Any], result)

        # Check if it's an error response
        if "message" in result_dict:
            Abort.require_condition(False, result_dict["message"])

        # Success case - it's a NotebookServer
        if getattr(ctx.obj, "json_output", False):
            print_json(data=result_dict)
        else:
            ctx.obj.console.print("📓 Creating notebook server...")
            ctx.obj.console.print(
                f"[green]✓[/green] Notebook server '[bold]{result_dict['name']}[/bold]' created successfully!"
            )
            ctx.obj.console.print(f"   Cluster: {result_dict['clusterName']}")
            ctx.obj.console.print(f"   Partition: {result_dict['partition']}")
            ctx.obj.console.print(f"   Owner: {result_dict['owner']}")
            if result_dict.get("serverUrl"):
                ctx.obj.console.print(f"   URL: {result_dict['serverUrl']}")
            if result_dict.get("slurmJobId"):
                ctx.obj.console.print(f"   SLURM Job ID: {result_dict['slurmJobId']}")

    except Exception as e:
        logger.error(f"Failed to create notebook server: {e}")
        Abort.require_condition(False, f"Failed to create notebook server: {e}")
