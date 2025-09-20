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
"""Delete notebook command."""

from typing import Any, Dict, Optional, cast

import typer
from rich import print_json
from typing_extensions import Annotated

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.gql_client import create_async_graphql_client


@handle_abort
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
            ctx.obj.console.print("[yellow]Deletion cancelled[/yellow]")
            return

    # The API only needs the notebook server name for deletion
    mutation = """
    mutation DeleteJupyterServer($notebookServerName: String!) {
        deleteJupyterServer(notebookServerName: $notebookServerName) {
            ... on NotebookServerDeleted {
                message
            }
            ... on NotebookServerNotFound {
                message
            }
        }
    }
    """

    variables: Dict[str, Any] = {"notebookServerName": name}

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

        # Handle union response - both types have message field
        message = delete_response_dict.get("message", "")

        # Check if it's a "not found" error by looking at the message content
        if "not found" in message.lower() or "does not exist" in message.lower():
            raise Abort(f"Notebook server not found: {message}")

        if getattr(ctx.obj, "json_output", False):
            result = {
                "name": name,
                "cluster": cluster,
                "status": "deleted",
                "message": message or f"Notebook server '{name}' has been deleted successfully",
            }
            print_json(data=result)
        else:
            if message:
                ctx.obj.console.print(f"[green]✓[/green] {message}")
            else:
                ctx.obj.console.print(
                    f"[green]✓[/green] Notebook server '{name}' has been deleted successfully"
                )

    except Exception as e:
        if "GraphQL errors:" in str(e) or "Failed to delete notebook server:" in str(e):
            raise
        raise Abort(f"Failed to delete notebook server: {e}")
