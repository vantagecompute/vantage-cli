# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Delete notebook command."""

from typing import Any, Dict, Optional, cast

import typer
from rich import print_json
from rich.console import Console
from typing_extensions import Annotated

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort
from vantage_cli.gql_client import create_async_graphql_client

console = Console()


@attach_settings
async def delete_notebook(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Notebook server name")],
    cluster: Annotated[Optional[str], typer.Option("--cluster", "-c", help="Cluster name")] = None,
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Force deletion without confirmation")
    ] = False,
):
    """Delete notebook server."""
    # Confirm deletion unless forced
    if not force:
        confirm = typer.confirm(f"Are you sure you want to delete notebook server '{name}'?")
        if not confirm:
            console.print("[yellow]Deletion cancelled[/yellow]")
            return

    mutation = """
    mutation DeleteJupyterServer($name: String!, $clusterName: String!) {
        deleteJupyterServer(name: $name, clusterName: $clusterName) {
            ... on NotebookServer {
                id
                name
                clusterName
                partition
                owner
            }
            ... on NotebookServerNotFound {
                message
            }
            ... on ClusterNotFound {
                message
            }
        }
    }
    """

    if not cluster:
        raise Abort("Cluster name is required for deleting notebook servers")

    variables: Dict[str, Any] = {"name": name, "clusterName": cluster}

    try:
        # Create async GraphQL client
        profile = getattr(ctx.obj, "profile", "default")
        graphql_client = create_async_graphql_client(ctx.obj.settings, profile)

        # Execute the mutation
        response_data = await graphql_client.execute_async(mutation, variables)

        if not response_data:
            raise Abort("No response from server")

        delete_response = response_data.get("deleteJupyterServer")

        if not delete_response:
            raise Abort("No delete response from server")

        # Ensure delete_response is a dictionary
        if not isinstance(delete_response, dict):
            raise Abort("Invalid response format from server")

        # Cast to help type checker
        delete_response_dict = cast(Dict[str, Any], delete_response)

        # Handle union response - check if it's an error
        if "message" in delete_response_dict and "id" not in delete_response_dict:
            raise Abort(f"Failed to delete notebook server: {delete_response_dict['message']}")

        if get_effective_json_output(ctx):
            result = {
                "name": delete_response_dict.get("name"),
                "cluster": delete_response_dict.get("clusterName"),
                "status": "deleted",
                "message": f"Notebook server '{delete_response_dict.get('name')}' has been deleted successfully",
            }
            print_json(data=result)
        else:
            console.print(
                f"[green]✓[/green] Notebook server '{delete_response_dict.get('name')}' has been deleted successfully"
            )

    except Exception as e:
        if "GraphQL errors:" in str(e) or "Failed to delete notebook server:" in str(e):
            raise
        raise Abort(f"Failed to delete notebook server: {e}")
