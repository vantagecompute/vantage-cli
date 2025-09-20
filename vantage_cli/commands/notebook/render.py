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
"""Render helpers for notebook command output formatting."""

from typing import Any, Dict, List, Optional

from rich.panel import Panel
from rich.table import Table

from vantage_cli.render import StyleMapper


def render_notebooks_table(
    notebooks: List[Dict[str, Any]],
    title: str = "Notebook Servers",
) -> Table:
    """Render a list of notebooks in a Rich table format.

    Args:
        notebooks: List of notebook dictionaries
        title: Title for the table
    """
    if not notebooks:
        return Table("No notebook servers found.", title="[yellow]No Results")

    # Define notebook-specific styling
    style_mapper = StyleMapper(
        name="bold cyan",
        clusterName="magenta",
        partition="green",
        owner="blue",
        serverUrl="yellow",
        slurmJobId="red",
        createdAt="dim white",
    )

    # Create the table
    table = Table(
        title=title,
        caption=f"Items: {len(notebooks)}",
        show_header=True,
        header_style="bold white",
    )

    # Define column order and display names
    column_mapping = {
        "name": "Name",
        "clusterName": "Cluster",
        "partition": "Partition",
        "owner": "Owner",
        "serverUrl": "Server URL",
        "slurmJobId": "SLURM Job ID",
        "createdAt": "Created",
    }

    # Add columns in the specified order
    for key, display_name in column_mapping.items():
        if notebooks and key in notebooks[0]:
            table.add_column(display_name, **style_mapper.map_style(key))

    # Add rows
    for notebook in notebooks:
        row_values = []
        for key in column_mapping.keys():
            if key in notebook:
                value = notebook.get(key, "")
                # Handle None values and format specific fields
                if value is None:
                    value = ""
                elif key == "createdAt" and isinstance(value, str) and len(value) > 10:
                    # Show just the date part
                    value = value[:10]
                elif key == "slurmJobId":
                    # Convert to string for display
                    value = str(value) if value is not None else ""
                row_values.append(str(value))
        table.add_row(*row_values)
    return table


def render_notebook_details(
    notebook: Dict[str, Any],
    title: Optional[str] = None,
) -> Panel:
    """Render notebook server details in a formatted panel.

    Args:
        notebook: Notebook dictionary with details
        console: Rich console for output
        title: Optional title for the panel
        json_output: If True, output as JSON instead of a panel
    """
    # Generate title if not provided
    if title is None:
        title = f"[bold cyan]Notebook Server: {notebook.get('name', '')}[/bold cyan]"

    # Build the details content
    details: List[str] = []
    details.append(f"[bold]Name:[/bold] {notebook.get('name', '')}")
    details.append(f"[bold]ID:[/bold] {notebook.get('id', '')}")
    details.append(f"[bold]Cluster:[/bold] {notebook.get('clusterName', '')}")
    details.append(f"[bold]Partition:[/bold] {notebook.get('partition', '')}")
    details.append(f"[bold]Owner:[/bold] {notebook.get('owner', '')}")
    details.append(f"[bold]Server URL:[/bold] {notebook.get('serverUrl', '')}")
    details.append(f"[bold]SLURM Job ID:[/bold] {notebook.get('slurmJobId', '')}")
    details.append(f"[bold]Created:[/bold] {notebook.get('createdAt', '')}")
    details.append(f"[bold]Updated:[/bold] {notebook.get('updatedAt', '')}")

    return Panel("\n".join(details), title=title, expand=False)
