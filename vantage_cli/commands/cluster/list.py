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
"""List clusters command."""

import typer
from loguru import logger

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.gql_client import create_async_graphql_client
from vantage_cli.render import render_quick_start_guide

from .render import render_clusters_table


@handle_abort
@attach_settings
async def list_clusters(
    ctx: typer.Context,
):
    """List all Vantage clusters."""
    # GraphQL query to fetch clusters
    query = """
    query getClusters($first: Int!) {
        clusters(first: $first) {
            edges {
                node {
                    name
                    status
                    clientId
                    description
                    ownerEmail
                    provider
                    cloudAccountId
                    creationParameters
                }
            }
            total
        }
    }
    """

    variables = {"first": 100}  # Fetch up to 100 clusters

    try:
        # Create async GraphQL client
        profile = getattr(ctx.obj, "profile", "default")
        graphql_client = create_async_graphql_client(ctx.obj.settings, profile)

        # Execute the query
        logger.debug("Executing clusters query")
        response_data = await graphql_client.execute_async(query, variables)

        # Extract cluster data
        clusters_data = response_data.get("clusters", {})
        clusters = [edge["node"] for edge in clusters_data.get("edges", [])]
        total_count = clusters_data.get("total", 0)

        # Get effective JSON output setting from context
        json_output = getattr(ctx.obj, "json_output", False) if ctx.obj else False
        effective_json = get_effective_json_output(ctx, json_output)

        # Render results using Rich table
        render_clusters_table(
            clusters,
            title="Clusters List",
            total_count=total_count,
            json_output=effective_json,
        )

        # Show quick start guide after listing clusters (only if not JSON output)
        if clusters and not effective_json:
            render_quick_start_guide()

    except Abort:
        # Re-raise Abort exceptions as they contain user-friendly messages
        raise
    except Exception as e:
        logger.error(f"Unexpected error listing clusters: {e}")
        raise Abort(
            "An unexpected error occurred while listing clusters.",
            subject="Unexpected Error",
            log_message=f"Unexpected error: {e}",
        )
