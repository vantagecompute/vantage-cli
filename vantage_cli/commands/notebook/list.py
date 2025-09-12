# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""List notebooks command."""

from typing import Any, Dict, List, Optional, cast

import typer
from rich import print_json
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort
from vantage_cli.gql_client import create_async_graphql_client

console = Console()


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
    query = """
    query NotebookServers($clusterName: String, $limit: Int) {
        notebookServers(clusterName: $clusterName, limit: $limit) {
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
    """

    variables: Dict[str, Any] = {}
    if cluster:
        variables["clusterName"] = cluster
    if limit:
        variables["limit"] = limit

    try:
        # Create async GraphQL client
        profile = getattr(ctx.obj, "profile", "default")
        graphql_client = create_async_graphql_client(ctx.obj.settings, profile)

        # Execute the query
        response_data = await graphql_client.execute_async(query, variables)

        if not response_data:
            raise Abort("No response from server")

        notebooks = response_data.get("notebookServers")

        if not notebooks:
            notebooks = []

        # Ensure notebooks is a list
        if not isinstance(notebooks, list):
            raise Abort("Invalid response format from server")

        # Cast to help type checker
        notebooks_list = cast(List[Dict[str, Any]], notebooks)

        if get_effective_json_output(ctx):
            result = {"total": len(notebooks_list), "notebooks": notebooks_list}
            print_json(data=result)
        else:
            if not notebooks_list:
                console.print("[yellow]No notebook servers found[/yellow]")
                return

            # Create and populate table
            table = Table(title="Notebook Servers")
            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Cluster", style="magenta")
            table.add_column("Partition", style="green")
            table.add_column("Owner", style="blue")
            table.add_column("Server URL", style="yellow")
            table.add_column("SLURM Job ID", style="red")
            table.add_column("Created", style="dim")

            for notebook in notebooks_list:
                table.add_row(
                    notebook.get("name", ""),
                    notebook.get("clusterName", ""),
                    notebook.get("partition", ""),
                    notebook.get("owner", ""),
                    notebook.get("serverUrl", ""),
                    str(notebook.get("slurmJobId", "")),
                    notebook.get("createdAt", "")[:10] if notebook.get("createdAt") else "",
                )

            console.print(table)

    except Exception as e:
        if "GraphQL errors:" in str(e):
            raise
        raise Abort(f"Failed to list notebook servers: {e}")

    if get_effective_json_output(ctx):
        # JSON output
        notebooks = [
            {
                "notebook_id": "notebook-123",
                "name": "data-analysis-notebook",
                "kernel": "python",
                "status": "running",
                "cells_count": 15,
            },
            {
                "notebook_id": "notebook-124",
                "name": "ml-training-notebook",
                "kernel": "python",
                "status": "stopped",
                "cells_count": 23,
            },
        ]

        # Apply filters
        if status:
            notebooks = [n for n in notebooks if n["status"] == status]
        if kernel:
            notebooks = [n for n in notebooks if n["kernel"] == kernel]

        print_json(
            data={
                "notebooks": notebooks[:limit] if limit else notebooks,
                "total": len(notebooks),
                "filters": {"status": status, "kernel": kernel, "limit": limit},
            }
        )
    else:
        # Rich console output
        console.print("📓 Notebooks:")
        console.print()

        notebooks = [
            ("notebook-123", "data-analysis-notebook", "python", "running", "15"),
            ("notebook-124", "ml-training-notebook", "python", "stopped", "23"),
        ]

        for nb_id, name, kern, stat, cells in notebooks:
            console.print(f"  🏷️  [bold blue]{nb_id}[/bold blue] - {name}")
            console.print(
                f"      Kernel: [cyan]{kern}[/cyan] | Status: [green]{stat}[/green] | Cells: [yellow]{cells}[/yellow]"
            )
            console.print()

        console.print(f"📊 Total notebooks: {len(notebooks)}")
