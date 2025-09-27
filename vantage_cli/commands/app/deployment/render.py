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
"""Render helpers for deployment command output formatting."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from rich import print_json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from vantage_cli.render import StyleMapper


def _format_datetime(datetime_str: str) -> str:
    """Format datetime string for display."""
    if datetime_str == "unknown" or not datetime_str:
        return "N/A"

    try:
        dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, AttributeError):
        return datetime_str


def render_deployments_table(
    deployments: List[Dict[str, Any]],
    console: Console,
    title: str = "Deployments List",
    total_count: Optional[int] = None,
    json_output: bool = False,
) -> None:
    """Render a list of deployments in a Rich table format.

    Args:
        deployments: List of deployment dictionaries
        console: Rich console for output
        title: Title for the table
        total_count: Total number of deployments available
        json_output: If True, output as JSON instead of a table
    """
    if json_output:
        # Output as JSON with Rich formatting
        output = {"deployments": deployments, "total": total_count or len(deployments)}
        print_json(data=output)
        return

    if not deployments:
        console.print()
        console.print(Panel("No deployments found.", title="[yellow]No Results"))
        console.print()
        return

    # Define deployment-specific styling
    style_mapper = StyleMapper(
        deployment_name="bold cyan",
        deployment_id="green",
        app_name="blue",
        cluster_name="yellow",
        cloud="white",
        status="magenta",
        created_at="dim white",
    )

    # Create the table
    table = Table(
        title=title,
        caption=f"Items: {len(deployments)}{f' of {total_count}' if total_count else ''}",
        show_header=True,
        header_style="bold white",
    )

    # Add columns based on the deployment list command format
    column_mapping = {
        "deployment_name": "Deployment Name",
        "deployment_id": "Deployment ID",
        "app_name": "App",
        "cluster_name": "Cluster",
        "cloud": "Cloud",
        "created_at": "Created",
        "status": "Status",
    }

    # Add columns in the specified order
    for key, display_name in column_mapping.items():
        if key == "deployment_name":
            table.add_column(display_name, **style_mapper.map_style(key))
        elif key == "deployment_id":
            table.add_column(display_name, **style_mapper.map_style(key))
        elif key == "app_name":
            table.add_column(display_name, **style_mapper.map_style(key), width=20)
        elif key == "cluster_name":
            table.add_column(display_name, **style_mapper.map_style(key), width=20)
        elif key == "cloud":
            table.add_column(display_name, **style_mapper.map_style(key), width=12)
        elif key == "created_at":
            table.add_column(display_name, **style_mapper.map_style(key), width=20)
        elif key == "status":
            table.add_column(display_name, **style_mapper.map_style(key), width=10)

    # Add rows
    for deployment in deployments:
        deployment_id = deployment.get("deployment_id", "unknown")
        deployment_name = deployment.get("deployment_name", "unknown")
        app_name = deployment.get("app_name", "unknown")
        cluster_name = deployment.get("cluster_name", "unknown")
        cloud_name = deployment.get("cloud", "unknown")
        created_at = deployment.get("created_at", "unknown")
        status = deployment.get("status", "unknown")

        # Format the created_at timestamp if it's an ISO format
        if created_at != "unknown":
            try:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                created_at = dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, AttributeError):
                # Keep original if parsing fails
                pass

        table.add_row(
            deployment_name,
            deployment_id,
            app_name,
            cluster_name,
            cloud_name,
            created_at,
            status,
        )

    # Print the table
    console.print()
    console.print(table)
    console.print()


def render_deployment_details(deployment: Dict[str, Any]) -> Table:
    """Render detailed information for a single deployment.

    Args:
        deployment: Deployment data dictionary

    Returns:
        Rich Table with deployment details
    """
    deployment_name = deployment.get("deployment_name", "Unknown")

    # Create a table matching the cluster get command style
    table = Table(
        title=f"Deployment Details: {deployment_name}", show_header=True, header_style="bold white"
    )

    table.add_column("Property", style="bold cyan")
    table.add_column("Value", style="white")

    # Add basic deployment information
    table.add_row("Deployment ID", deployment.get("deployment_id", "N/A"))
    table.add_row("Deployment Name", deployment.get("deployment_name", "N/A"))
    table.add_row("App Name", deployment.get("app_name", "N/A"))
    table.add_row("Cluster Name", deployment.get("cluster_name", "N/A"))
    table.add_row("Cluster ID", deployment.get("cluster_id", "N/A"))
    table.add_row("Cloud", deployment.get("cloud", "N/A"))
    table.add_row("Cloud Type", deployment.get("cloud_type", "N/A"))

    # Format status with color
    status = deployment.get("status", "N/A")
    status_colors = {
        "active": "green",
        "inactive": "yellow",
        "error": "red",
        "init": "blue",
        "pending": "yellow",
    }
    status_color = status_colors.get(status.lower(), "white")
    status_display = f"[{status_color}]{status}[/{status_color}]"
    table.add_row("Status", status_display)

    table.add_row("Created At", _format_datetime(deployment.get("created_at", "N/A")))
    table.add_row("Updated At", _format_datetime(deployment.get("updated_at", "N/A")))

    # Add client ID if available
    client_id = deployment.get("client_id")
    if client_id and client_id != "unknown":
        table.add_row("Client ID", client_id)

    # Add K8s namespaces if available
    k8s_namespaces = deployment.get("k8s_namespaces", [])
    if k8s_namespaces:
        namespaces_str = ", ".join(k8s_namespaces)
        table.add_row("K8s Namespaces", namespaces_str)
    else:
        table.add_row("K8s Namespaces", "None")

    # Add metadata if available
    metadata = deployment.get("metadata", {})
    if metadata:
        # Add a separator row
        table.add_row("", "")  # Empty row for spacing
        table.add_row("[bold]Deployment Metadata[/bold]", "")

        for key, value in metadata.items():
            if value is not None:
                # Format key for display
                display_key = key.replace("_", " ").title()
                if isinstance(value, (dict, list)):
                    display_value = str(value)
                else:
                    display_value = str(value)
                table.add_row(f"  {display_key}", display_value)

    # Add cluster data if available
    cluster_data = deployment.get("cluster_data", {})
    if cluster_data:
        # Add a separator row
        table.add_row("", "")  # Empty row for spacing
        table.add_row("[bold]Cluster Information[/bold]", "")

        # Display key cluster properties in a nice order
        key_properties = [
            ("name", "Name"),
            ("clientId", "Client ID"),
            ("status", "Status"),
            ("provider", "Provider"),
            ("description", "Description"),
            ("ownerEmail", "Owner Email"),
            ("cloudAccountId", "Cloud Account ID"),
            ("deployment_name", "Deployment Name"),
        ]

        # Add key properties first
        for prop_key, display_name in key_properties:
            if prop_key in cluster_data:
                value = cluster_data[prop_key]
                if value is not None:
                    display_value = str(value) if value != "" else "N/A"
                    table.add_row(f"  {display_name}", display_value)

        # Add creation parameters if available
        creation_params = cluster_data.get("creationParameters", {})
        if creation_params:
            table.add_row("", "")  # Empty row for spacing
            table.add_row("[bold]Creation Parameters[/bold]", "")

            for key, value in creation_params.items():
                if value is not None:
                    display_key = key.replace("_", " ").title()
                    # Mask sensitive data like tokens
                    if "token" in key.lower() and isinstance(value, str):
                        display_value = (
                            f"[dim]{value[:8]}...{value[-8:]}[/dim]"
                            if len(value) > 16
                            else f"[dim]{value}[/dim]"
                        )
                    else:
                        display_value = (
                            str(value) if not isinstance(value, dict) else "Complex Object"
                        )
                    table.add_row(f"  {display_key}", display_value)

    return table


def render_deployment_creation_result(
    deployment: Dict[str, Any], console: Console, json_output: bool = False
) -> None:
    """Render the result of deployment creation.

    Args:
        deployment: Created deployment dictionary
        console: Console instance for output
        json_output: If True, output as JSON instead of a formatted view
    """
    if json_output:
        print_json(data=deployment)
        return

    console.print()
    console.print(
        Panel(
            f"✅ Deployment '[bold cyan]{deployment.get('deployment_name', 'Unknown')}[/bold cyan]' created successfully!",
            title="[green]Deployment Created[/green]",
            border_style="green",
        )
    )

    # Show basic details
    console.print()
    console.print(render_deployment_details(deployment))
