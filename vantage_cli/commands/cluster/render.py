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
"""Render helpers for cluster command output formatting."""

from typing import Any, Dict, List, Optional

from rich import print_json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from vantage_cli.render import StyleMapper


def render_clusters_table(
    clusters: List[Dict[str, Any]],
    console: Console,
    title: str = "Clusters List",
    total_count: Optional[int] = None,
    json_output: bool = False,
) -> None:
    """Render a list of clusters in a Rich table format.

    Args:
        clusters: List of cluster dictionaries
        console: Rich console for output
        title: Title for the table
        total_count: Total number of clusters available
        json_output: If True, output as JSON instead of a table
    """
    if json_output:
        # Output as JSON with Rich formatting
        output = {"clusters": clusters, "total": total_count or len(clusters)}
        print_json(data=output)
        return

    if not clusters:
        console.print()
        console.print(Panel("No clusters found.", title="[yellow]No Results"))
        console.print()
        return

    # Define cluster-specific styling
    style_mapper = StyleMapper(
        name="bold cyan",
        status="green",
        provider="blue",
        ownerEmail="yellow",
        clientId="white",
        description="dim white",
    )

    # Create the table
    table = Table(
        title=title,
        caption=f"Items: {len(clusters)}{f' of {total_count}' if total_count else ''}",
        show_header=True,
        header_style="bold white",
    )

    # Add columns based on the first cluster's keys
    first_cluster = clusters[0]

    # Define column order and display names
    column_mapping = {
        "name": "Name",
        "status": "Status",
        "provider": "Provider",
        "ownerEmail": "Owner Email",
        "clientId": "Client ID",
        "description": "Description",
    }

    # Add columns in the specified order
    for key, display_name in column_mapping.items():
        if key in first_cluster:
            table.add_column(display_name, **style_mapper.map_style(key))

    # Add rows
    for cluster in clusters:
        row_values = []
        for key in column_mapping.keys():
            if key in cluster:
                value = cluster.get(key, "")
                # Handle None values and long descriptions
                if value is None:
                    value = ""
                elif key == "description" and isinstance(value, str) and len(value) > 50:
                    value = value[:47] + "..."
                row_values.append(str(value))
        table.add_row(*row_values)

    # Print the table
    console.print()
    console.print(table)
    console.print()


def render_cluster_details(cluster: Dict[str, Any]) -> Table:
    """Render detailed information for a single cluster.

    Args:
        cluster: Cluster data dictionary
        console: Rich console for output
        json_output: If True, output as JSON instead of a table
    """
    cluster_name = cluster.get("name", "Unknown")

    # Create a table matching the profile get command style
    table = Table(
        title=f"Cluster Details: {cluster_name}", show_header=True, header_style="bold white"
    )

    table.add_column("Property", style="bold cyan")
    table.add_column("Value", style="white")

    # Add basic cluster information
    table.add_row("Name", cluster.get("name", "N/A"))
    table.add_row("Status", cluster.get("status", "N/A"))
    table.add_row("Provider", cluster.get("provider", "N/A"))
    table.add_row("Owner Email", cluster.get("ownerEmail", "N/A"))
    table.add_row("Client ID", cluster.get("clientId", "N/A"))

    # Add client secret if available
    client_secret = cluster.get("client_secret")
    if client_secret:
        table.add_row("Client Secret", f"[dim]{client_secret}[/dim]")
    else:
        table.add_row("Client Secret", "[dim]Not available[/dim]")

    table.add_row("Description", cluster.get("description", "N/A"))

    cloud_account_id = cluster.get("cloudAccountId")
    table.add_row(
        "Cloud Account ID", str(cloud_account_id) if cloud_account_id is not None else "None"
    )

    # Add creation parameters if available
    creation_params = cluster.get("creationParameters", {})
    if creation_params:
        # Add a separator row
        table.add_row("", "")  # Empty row for spacing
        table.add_row("[bold]Creation Parameters[/bold]", "")

        for key, value in creation_params.items():
            if value is not None:
                # Format key for display
                display_key = key.replace("_", " ").title()
                display_value = str(value) if not isinstance(value, dict) else "Complex Object"
                table.add_row(f"  {display_key}", display_value)

    return table


def render_cluster_creation_result(
    cluster: Dict[str, Any], console: Console, json_output: bool = False
) -> None:
    """Render the result of cluster creation.

    Args:
        cluster: Created cluster dictionary
        console: Console instance for output
        json_output: If True, output as JSON instead of a formatted view
    """
    if json_output:
        print_json(data=cluster)
        return

    console.print()
    console.print(
        Panel(
            f"✅ Cluster '[bold cyan]{cluster.get('name', 'Unknown')}[/bold cyan]' created successfully!",
            title="[green]Cluster Created[/green]",
            border_style="green",
        )
    )

    # Show basic details
    console.print()
    console.print(render_cluster_details(cluster))


def render_cluster_deletion_table(cluster_name: str, success: bool = True) -> Table:
    """Render the result of cluster deletion.

    Args:
        cluster_name: Name of the deleted cluster
        success: Whether deletion was successful
    """
    table = Table(
        title=f"Cluster Deletion: {cluster_name}", show_header=True, header_style="bold white"
    )
    table.add_column("Status", style="bold cyan")
    table.add_column("Message", style="white")

    if success:
        table.add_row(
            "✅ Deleted", f"Cluster '[bold cyan]{cluster_name}[/bold cyan]' deleted successfully!"
        )
    else:
        table.add_row(
            "❌ Failed", f"Failed to delete cluster '[bold cyan]{cluster_name}[/bold cyan]'"
        )

    return table
