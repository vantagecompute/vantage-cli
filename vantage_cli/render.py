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
"""Rendering utilities for CLI output."""

from typing import Any, Dict

import snick
from rich.console import Console
from rich.panel import Panel


class StyleMapper:
    """Provide a mapper that can set Rich styles for rendered output of data tables.

    Similar to jobbergate-cli's StyleMapper, this class provides a way to define
    styles that should be applied to columns of tables.
    """

    def __init__(self, **colors: str):
        """Initialize the StyleMapper with color mappings."""
        self.colors = colors

    def map_style(self, column: str) -> Dict[str, Any]:
        """Map a column name to the style that should be used to render it."""
        color = self.colors.get(column, "white")
        return {
            "style": color,
            "header_style": f"bold {color}",
        }


def render_quick_start_guide() -> None:
    """Render quick start guide for the CLI."""
    """Render a quick start guide panel similar to jobbergate-cli's demo."""
    message = snick.dedent(
        """
        • To view cluster details, use the command: vantage clusters get

        • To create a new cluster, use the command: vantage clusters create --help

        • For more information on any command run it with the --help option.

        • To check all the available commands, refer to: vantage --help
        """
    ).strip()

    console = Console()
    panel = Panel(
        message,
        title="[bold magenta]Quick Start Guide for Vantage-CLI[/bold magenta]",
        border_style="blue",
        expand=False,
    )

    console.print()
    console.print(panel)
