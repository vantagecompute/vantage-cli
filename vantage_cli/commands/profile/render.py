# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Render helpers for profile command output formatting."""

from typing import Any, Dict, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def render_profile_operation_result(
    operation: str,
    profile_name: str,
    success: bool = True,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Render the result of a profile operation.

    Args:
        operation: The operation performed (create, delete, update)
        profile_name: Name of the profile
        success: Whether the operation was successful
        details: Additional details about the operation
    """
    console = Console()
    console.print()

    status_icon = "✅" if success else "❌"
    status_color = "green" if success else "red"
    action_text = f"{operation.title()}d" if success else f"{operation.title()} Failed"

    console.print(
        Panel(
            f"{status_icon} Profile '[bold cyan]{profile_name}[/bold cyan]' {operation} {'successful' if success else 'failed'}!",
            title=f"[{status_color}]{action_text}[/{status_color}]",
            border_style=status_color,
        )
    )

    if details:
        # Show additional details if provided
        details_table = Table(title="Profile Details", show_header=False, box=None, padding=(0, 1))
        details_table.add_column("Field", style="bold blue", width=20)
        details_table.add_column("Value", style="white")

        for key, value in details.items():
            if value is not None:
                display_key = key.replace("_", " ").title()
                details_table.add_row(display_key, str(value))

        console.print()
        console.print(details_table)

    console.print()
