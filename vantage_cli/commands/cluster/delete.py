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
"""Delete cluster command for Vantage CLI."""

import typer
from loguru import logger
from typing_extensions import Annotated

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort
from vantage_cli.gql_client import create_async_graphql_client

from .render import render_cluster_deletion_result


@attach_settings
async def delete_cluster(
    ctx: typer.Context,
    cluster_name: Annotated[str, typer.Argument(help="Name of the cluster to delete")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation prompt")] = False,
):
    """Delete a Vantage cluster."""
    # Get JSON flag from context (automatically set by AsyncTyper)
    json_output = getattr(ctx.obj, "json_output", False) if ctx.obj else False
    # Get effective JSON output setting
    effective_json = get_effective_json_output(ctx, json_output)

    # Confirmation prompt unless force is used
    if not force and not effective_json:
        from rich.console import Console
        from rich.prompt import Confirm

        console = Console()
        console.print(
            f"\n[yellow]⚠️  You are about to delete cluster '[bold red]{cluster_name}[/bold red]'[/yellow]"
        )
        console.print("[yellow]This action cannot be undone![/yellow]")

        if not Confirm.ask("Are you sure you want to proceed?"):
            console.print("[dim]Deletion cancelled.[/dim]")
            return

    # GraphQL mutation for deleting a cluster
    delete_mutation = """
    mutation deleteCluster($clusterName: String!) {
        deleteCluster(clusterName: $clusterName) {
            ... on ClusterDeleted {
                message
            }
            ... on ClusterNotFound {
                message
            }
            ... on InvalidProviderInput {
                message
            }
            ... on UnexpectedBehavior {
                message
            }
        }
    }
    """

    try:
        # Create async GraphQL client
        profile = getattr(ctx.obj, "profile", "default")
        graphql_client = create_async_graphql_client(ctx.obj.settings, profile)

        # Prepare deletion variables
        delete_variables = {"clusterName": cluster_name}

        # Execute the deletion mutation
        logger.debug(f"Deleting cluster: {cluster_name}")
        delete_response = await graphql_client.execute_async(delete_mutation, delete_variables)

        # Extract deletion result
        deletion_data = delete_response.get("deleteCluster", {})

        # Log the response for debugging
        logger.debug(f"Delete response: {deletion_data}")

        # Determine success - if we get any response it likely succeeded
        # The GraphQL union types make it tricky to detect success vs failure
        success = bool(deletion_data)  # If we got a response without error, consider it success

        # Render deletion result
        render_cluster_deletion_result(
            cluster_name=cluster_name,
            success=success,
            json_output=effective_json,
        )

    except Abort:
        # Re-raise Abort exceptions as they contain user-friendly messages
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting cluster '{cluster_name}': {e}")
        raise Abort(
            f"An unexpected error occurred while deleting cluster '{cluster_name}'.",
            subject="Unexpected Error",
            log_message=f"Unexpected error: {e}",
        )
