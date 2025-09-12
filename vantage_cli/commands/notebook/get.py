# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Get notebook command."""

from typing import Any, Dict, List, Optional, cast

import typer
from rich import print_json
from rich.console import Console
from rich.panel import Panel
from typing_extensions import Annotated

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort
from vantage_cli.gql_client import create_async_graphql_client

console = Console()


@attach_settings
async def get_notebook(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Notebook server name")],
    cluster: Annotated[Optional[str], typer.Option("--cluster", "-c", help="Cluster name")] = None,
):
    """Get notebook server details."""
    query = """
    query NotebookServer($name: String!, $clusterName: String) {
        notebookServer(name: $name, clusterName: $clusterName) {
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
            ... on NotebookServerNotFound {
                message
            }
        }
    }
    """

    variables: Dict[str, Any] = {"name": name}
    if cluster:
        variables["clusterName"] = cluster

    try:
        # Create async GraphQL client
        profile = getattr(ctx.obj, "profile", "default")
        graphql_client = create_async_graphql_client(ctx.obj.settings, profile)

        # Execute the query
        response_data = await graphql_client.execute_async(query, variables)

        if not response_data:
            raise Abort("No response from server")

        notebook_response = response_data.get("notebookServer")

        if not notebook_response:
            raise Abort("No notebook response from server")

        # Ensure notebook_response is a dictionary
        if not isinstance(notebook_response, dict):
            raise Abort("Invalid response format from server")

        # Cast to help type checker
        notebook_response_dict = cast(Dict[str, Any], notebook_response)

        # Handle union response - check if it's an error
        if "message" in notebook_response_dict:
            raise Abort(f"Notebook server not found: {notebook_response_dict['message']}")

        if get_effective_json_output(ctx):
            print_json(data=notebook_response_dict)
        else:
            # Display notebook details in a formatted panel
            details: List[str] = []
            details.append(f"[bold]Name:[/bold] {notebook_response_dict.get('name', '')}")
            details.append(f"[bold]ID:[/bold] {notebook_response_dict.get('id', '')}")
            details.append(
                f"[bold]Cluster:[/bold] {notebook_response_dict.get('clusterName', '')}"
            )
            details.append(
                f"[bold]Partition:[/bold] {notebook_response_dict.get('partition', '')}"
            )
            details.append(f"[bold]Owner:[/bold] {notebook_response_dict.get('owner', '')}")
            details.append(
                f"[bold]Server URL:[/bold] {notebook_response_dict.get('serverUrl', '')}"
            )
            details.append(
                f"[bold]SLURM Job ID:[/bold] {notebook_response_dict.get('slurmJobId', '')}"
            )
            details.append(f"[bold]Created:[/bold] {notebook_response_dict.get('createdAt', '')}")
            details.append(f"[bold]Updated:[/bold] {notebook_response_dict.get('updatedAt', '')}")

            panel_content = "\n".join(details)
            panel = Panel(
                panel_content,
                title=f"[bold cyan]Notebook Server: {notebook_response_dict.get('name', '')}[/bold cyan]",
                expand=False,
            )
            console.print(panel)

    except Exception as e:
        if "GraphQL errors:" in str(e) or "Notebook server not found:" in str(e):
            raise
        raise Abort(f"Failed to get notebook server: {e}")
