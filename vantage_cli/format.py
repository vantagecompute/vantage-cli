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
"""Output formatting utilities for the Vantage CLI."""

import json
from typing import Any, Optional

import snick
from rich.console import Console
from rich.panel import Panel


def terminal_message(
    message: str,
    subject: Optional[str],
    color: str = "green",
    footer: Optional[str] = None,
    indent: bool = True,
):
    """Display a formatted message in the terminal."""
    text = snick.dedent(message)
    if indent:
        text = snick.indent(text, prefix="  ")
    console = Console()
    console.print()

    # Build panel with explicit parameters
    panel_title = f"[{color}]{subject}" if subject is not None else None
    panel_subtitle = f"[dim italic]{footer}[/dim italic]" if footer is not None else None
    panel = Panel(text, title=panel_title, subtitle=panel_subtitle, padding=(1, 1))

    console.print(panel)
    console.print()


def render_json(data: Any) -> None:
    """Render data as formatted JSON output."""
    console = Console()
    console.print()
    console.print_json(json.dumps(data))
    console.print()
