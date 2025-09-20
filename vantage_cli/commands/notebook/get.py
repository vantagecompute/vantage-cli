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
"""Get notebook command."""

from typing import Any, Dict, cast

import typer
from typing_extensions import Annotated

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.gql_client import create_async_graphql_client
from vantage_cli.render import RenderStepOutput

from .render import render_notebook_details


@handle_abort
@attach_settings
async def get_notebook(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Notebook server name")],
):
    """Get notebook server details."""
    renderer = RenderStepOutput(
        console=ctx.obj.console,
        operation_name="Get a Notebook",
        step_names=["Complete"],
        use_panel=False,
        show_start_message=False,
        command_start_time=getattr(ctx.obj, "command_start_time", None) if ctx.obj else None,
    )
    # Since the API doesn't support a singular notebookServer query,
    # we'll use the notebookServers list query and filter by name
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

    variables: Dict[str, Any] = {"first": 100}  # Get a reasonable number of notebooks

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

        # Filter by name and optionally by cluster
        matching_notebooks = []
        for notebook in notebooks:
            if notebook.get("name") == name:
                matching_notebooks.append(notebook)

        if not matching_notebooks:
            raise Abort(f"Notebook server '{name}' not found")

        if len(matching_notebooks) > 1:
            ctx.obj.console.print(
                "[yellow]Warning: Multiple notebook servers found with the same name[/yellow]"
            )

        notebook_response = matching_notebooks[0]  # Use the first match

        # Cast to help type checker
        notebook_response_dict = cast(Dict[str, Any], notebook_response)

        # Get effective JSON output setting from context
        if getattr(ctx.obj, "json_output", False):
            renderer.json_bypass(notebook_response_dict)
            return

        notebook_panel = render_notebook_details(
            notebook_response_dict,
        )

        with renderer:
            renderer.panel_step(notebook_panel)
            renderer.complete_step("Complete")

    except Exception as e:
        if "GraphQL errors:" in str(e) or "notebook server not found" in str(e):
            raise
        raise Abort(f"Failed to get notebook server: {e}")
