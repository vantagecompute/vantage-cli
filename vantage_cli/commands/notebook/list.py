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
"""List notebooks command."""

from typing import Any, Dict, List, Optional, cast

import typer
from typing_extensions import Annotated

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.gql_client import create_async_graphql_client
from vantage_cli.render import RenderStepOutput

from .render import render_notebooks_table


@handle_abort
@attach_settings
async def list_notebooks(
    ctx: typer.Context,
    cluster: Annotated[
        Optional[str], typer.Option("--cluster", "-c", help="Filter by cluster name")
    ] = None,
    status: Annotated[
        Optional[str], typer.Option("--status", "-s", help="Filter by notebook status")
    ] = None,
    kernel: Annotated[
        Optional[str], typer.Option("--kernel", "-k", help="Filter by kernel type")
    ] = None,
    limit: Annotated[
        Optional[int], typer.Option("--limit", "-l", help="Maximum number of notebooks to return")
    ] = None,
):
    """List notebook servers."""
    renderer = RenderStepOutput(
        console=ctx.obj.console,
        operation_name="List Notebooks",
        step_names=["Complete"],  # "Querying", "Rendering"],
        use_panel=False,
        show_start_message=False,
        command_start_time=getattr(ctx.obj, "command_start_time", None) if ctx.obj else None,
    )

    query = """
    query NotebookServers($first: Int) {
        notebookServers(first: $first) {
            edges {
                node {
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
            }
            total
        }
    }
    """

    variables: Dict[str, Any] = {}
    if limit:
        variables["first"] = limit
    else:
        variables["first"] = 100  # Default limit

    try:
        # Create async GraphQL client
        profile = getattr(ctx.obj, "profile", "default")
        graphql_client = create_async_graphql_client(ctx.obj.settings, profile)

        # Execute the query
        response_data = await graphql_client.execute_async(query, variables)

        if not response_data:
            raise Abort("No response from server")

        notebooks_data = response_data.get("notebookServers", {})
        notebooks = [edge["node"] for edge in notebooks_data.get("edges", [])]

        if not notebooks:
            notebooks = []

        # Cast to help type checker
        notebooks_list = cast(List[Dict[str, Any]], notebooks)

        # Apply client-side filters
        if cluster:
            notebooks_list = [n for n in notebooks_list if n.get("clusterName") == cluster]
        # Note: status and kernel filters are not available in the API schema
        # but the CLI parameters are kept for potential future use

        # Get effective JSON output setting from context
        json_output = getattr(ctx.obj, "json_output", False)
        if json_output:
            renderer.json_bypass(notebooks_list)
            return

        notebooks_table = render_notebooks_table(
            notebooks_list,
            title="Notebook Servers",
        )
        with renderer:
            renderer.table_step(notebooks_table)
            renderer.complete_step("Complete")

    except Exception as e:
        if "GraphQL errors:" in str(e):
            raise
        raise Abort(f"Failed to list notebook servers: {e}")
