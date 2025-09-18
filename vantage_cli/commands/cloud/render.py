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
"""Render helpers for cloud command output formatting."""

from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from vantage_cli.render import StyleMapper


def render_clouds_table(
    clouds: List[Dict[str, Any]],
    console: Console,
    title: str = "Cloud Accounts",
    total_count: Optional[int] = None,
    json_output: bool = False,
) -> None:
    """Render a list of cloud accounts in a Rich table format.

    Args:
        clouds: List of cloud account dictionaries
        console: Console instance for output
        title: Title for the table
        total_count: Total number of cloud accounts available
        json_output: If True, output as JSON instead of a table
    """
    if json_output:
        output = {"clouds": clouds, "total": total_count or len(clouds)}
        console.print_json(data=output)
        return

    if not clouds:
        console.print()
        console.print(Panel("No cloud accounts found.", title="[yellow]No Results"))
        console.print()
        return

    # Define cloud-specific styling
    style_mapper = StyleMapper(
        name="bold cyan", provider="blue", status="green", accountId="white", region="yellow"
    )

    # Create the table
    table = Table(
        title=title,
        caption=f"Items: {len(clouds)}{f' of {total_count}' if total_count else ''}",
        show_header=True,
        header_style="bold white",
    )

    # Add columns based on cloud data structure
    column_mapping = {
        "name": "Name",
        "provider": "Provider",
        "status": "Status",
        "accountId": "Account ID",
        "region": "Region",
    }

    # Add columns that exist in the first cloud entry
    if clouds:
        first_cloud = clouds[0]
        for key, display_name in column_mapping.items():
            if key in first_cloud:
                table.add_column(display_name, **style_mapper.map_style(key))

    # Add rows
    for cloud in clouds:
        row_values = []
        for key in column_mapping.keys():
            if key in cloud:
                value = cloud.get(key, "")
                if value is None:
                    value = ""
                row_values.append(str(value))
        if row_values:  # Only add row if we have values
            table.add_row(*row_values)

    # Print the table
    console.print()
    console.print(table)
    console.print()


def render_cloud_operation_result(
    operation: str,
    cloud_name: str,
    console: Console,
    success: bool = True,
    details: Optional[Dict[str, Any]] = None,
    json_output: bool = False,
) -> None:
    """Render the result of a cloud operation (add, update, delete).

    Args:
        operation: The operation performed (add, update, delete)
        cloud_name: Name of the cloud account
        console: Console instance for output
        success: Whether the operation was successful
        details: Additional details about the operation
        json_output: If True, output as JSON instead of a formatted view
    """
    if json_output:
        result = {
            "operation": operation,
            "cloud_name": cloud_name,
            "success": success,
            "details": details or {},
        }
        console.print_json(data=result)
        return

    console.print()

    status_icon = "✅" if success else "❌"
    status_color = "green" if success else "red"
    action_text = f"{operation.title()}d" if success else f"{operation.title()} Failed"

    console.print(
        Panel(
            f"{status_icon} Cloud account '[bold cyan]{cloud_name}[/bold cyan]' {operation} {'successful' if success else 'failed'}!",
            title=f"[{status_color}]{action_text}[/{status_color}]",
            border_style=status_color,
        )
    )

    if details and not json_output:
        # Show additional details if provided
        details_table = Table(
            title="Operation Details", show_header=False, box=None, padding=(0, 1)
        )
        details_table.add_column("Field", style="bold blue", width=20)
        details_table.add_column("Value", style="white")

        for key, value in details.items():
            if value is not None:
                display_key = key.replace("_", " ").title()
                details_table.add_row(display_key, str(value))

        console.print()
        console.print(details_table)

    console.print()
