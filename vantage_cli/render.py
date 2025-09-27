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

import json
import shutil
import time
from contextlib import contextmanager
from types import TracebackType
from typing import Any, Callable, Dict, List, Optional

import snick
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, ProgressColumn, SpinnerColumn, Task, TextColumn
from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Footer, Header


class TableViewerApp(App):
    """Textual app for displaying data tables with auto-layout."""

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("escape", "quit", "Quit", priority=True),
    ]

    def __init__(self, data: List[Dict[str, Any]], title: str = "", **kwargs):
        super().__init__(**kwargs)
        self.data = data
        self.title = title

    def compose(self) -> ComposeResult:
        """Create the table widget."""
        if self.title:
            yield Header(show_clock=False)

        data_table = DataTable(show_cursor=False, zebra_stripes=True)
        data_table.cursor_type = "none"
        yield data_table

        if self.title:
            yield Footer()

    def on_mount(self) -> None:
        """Set up the table when the app mounts."""
        if not self.data:
            return

        table = self.query_one(DataTable)

        # Get all unique keys from all items
        all_keys = set()
        for item in self.data:
            if isinstance(item, dict):
                all_keys.update(item.keys())

        # Sort keys with common fields first
        common_fields = [
            "id",
            "name",
            "title",
            "description",
            "status",
            "created_at",
            "updated_at",
        ]
        sorted_keys = []

        for field in common_fields:
            if field in all_keys:
                sorted_keys.append(field)
                all_keys.remove(field)

        sorted_keys.extend(sorted(all_keys))

        # Add columns
        for key in sorted_keys:
            header = self._format_column_header(key)
            table.add_column(header, key=key)

        # Add rows
        for item in self.data:
            row_data = []
            for key in sorted_keys:
                value = item.get(key, "")
                formatted_value = self._format_cell_value(key, value)
                row_data.append(formatted_value)
            table.add_row(*row_data)

        if self.title:
            self.title = self.title

    def _format_column_header(self, key: str) -> str:
        """Format column header nicely."""
        # Handle special cases first
        special_cases = {
            "id": "ID",
            "url": "URL",
            "api": "API",
            "cpu": "CPU",
            "gpu": "GPU",
            "ram": "RAM",
            "ssh": "SSH",
            "uuid": "UUID",
            "cidr": "CIDR",
            "ip": "IP",
        }

        if key.lower() in special_cases:
            return special_cases[key.lower()]

        # Split on underscores and capitalize each word
        words = key.split("_")
        formatted_words = []
        for word in words:
            if word.lower() in special_cases:
                formatted_words.append(special_cases[word.lower()])
            else:
                formatted_words.append(word.capitalize())

        return " ".join(formatted_words)

    def _format_cell_value(self, key: str, value: Any) -> str:
        """Format a cell value for display."""
        if value is None:
            return "N/A"
        elif value == "":
            return "N/A"
        elif isinstance(value, bool):
            return "✓" if value else "✗"
        elif isinstance(value, (list, dict)):
            # For complex nested data, show a summary
            if isinstance(value, list):
                return f"[{len(value)} items]" if value else "[]"
            else:
                return f"[{len(value)} keys]" if value else "{}"
        elif isinstance(value, str):
            # Handle common formatting cases
            if key.lower().endswith("_at") or "date" in key.lower():
                # Try to format dates nicely, fallback to original
                try:
                    from datetime import datetime

                    if "T" in value and value.endswith("Z"):
                        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                        return dt.strftime("%Y-%m-%d")
                    return value
                except Exception:
                    return value
            elif key.lower() in ["status", "state"]:
                return value.upper()
            else:
                # Truncate strings based on field-specific limits to prevent wrapping
                max_length = self._get_field_max_length(key)
                if len(value) > max_length:
                    return value[: max_length - 3] + "..."
                return value
        else:
            return str(value)

    def _get_field_max_length(self, key: str) -> int:
        """Get maximum character length for a field value."""
        key_lower = key.lower()

        if key_lower == "description":
            return 50
        elif key_lower in ["name", "title"]:
            return 30
        elif key_lower in ["email", "url"]:
            return 35
        elif key_lower == "id":
            return 15
        else:
            return 25

    def _render_static_table(
        self, items: List[Dict[str, Any]], title: str, console: Console
    ) -> None:
        """Render a static table using Rich console (for non-interactive mode)."""
        from rich.table import Table

        if not items:
            return

        # Create Rich table for static rendering
        table = Table(
            title=title if title else None, show_header=True, header_style="bold magenta"
        )

        # Get all unique keys from all items
        all_keys = set()
        for item in items:
            if isinstance(item, dict):
                all_keys.update(item.keys())

        # Sort keys with common fields first
        common_fields = [
            "id",
            "name",
            "title",
            "description",
            "status",
            "created_at",
            "updated_at",
        ]
        sorted_keys = []

        for field in common_fields:
            if field in all_keys:
                sorted_keys.append(field)
                all_keys.remove(field)

        sorted_keys.extend(sorted(all_keys))

        # Add columns (Textual will auto-size these)
        for key in sorted_keys:
            header = self._format_column_header(key)
            table.add_column(header, no_wrap=True)

        # Add rows
        for item in items:
            row_data = []
            for key in sorted_keys:
                value = item.get(key, "")
                formatted_value = self._format_cell_value(key, value)
                row_data.append(formatted_value)
            table.add_row(*row_data)

        console.print(table)


class CommandTimeElapsedColumn(ProgressColumn):
    """Displays elapsed time from command start rather than progress start."""

    def __init__(self, command_start_time: Optional[float] = None):
        super().__init__()
        self.command_start_time = command_start_time

    def render(self, task: Task) -> Text:
        """Render the elapsed time from command start with high granularity."""
        if self.command_start_time is not None:
            elapsed = time.time() - self.command_start_time
        else:
            # Fallback to task elapsed time if command start time not available
            elapsed = task.elapsed or 0

        # Format with millisecond precision for better granularity
        if elapsed < 1.0:
            # For very short times (< 1 second), show milliseconds only
            time_text = f"{elapsed:.3f}s"
        else:
            # For times >= 1 second, show with millisecond precision
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = elapsed % 60  # Keep as float for milliseconds

            if hours > 0:
                time_text = f"{hours}:{minutes:02d}:{seconds:06.3f}"
            else:
                time_text = f"{minutes}:{seconds:06.3f}"

        return Text(time_text, style="progress.elapsed")


@contextmanager
def single_progress_panel(
    operation_name: str,
    console: Console,
    command_start_time: Optional[float] = None,
):
    """Context manager for a single updating progress panel.

    Shows one panel with a title that updates to show current step and elapsed time.

    Args:
        operation_name: Base name of the operation
        console: Rich console for output
        command_start_time: Start time of the command for accurate timing

    Yields:
        Function to call with (step_name, status) to update the panel
    """
    start_time = command_start_time or time.time()
    current_step = "Initializing"

    # Create progress display with spinner and elapsed time
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        CommandTimeElapsedColumn(command_start_time=start_time),
        console=console,
        transient=False,
    )

    # Add a task for this operation
    task_id = progress.add_task("", total=None)

    def update_step(step_name: str, status: str = "starting"):
        """Update the current step being displayed."""
        nonlocal current_step
        current_step = step_name

        # Update the task description to show current step
        progress.update(task_id, description=f"{operation_name} - {step_name}")

    # Create the panel with Live updating
    with Live(
        Panel(progress, title=f"[blue]{operation_name}[/blue]", padding=(0, 1)),
        console=console,
        refresh_per_second=10,
        transient=False,
    ):
        try:
            # Return the update function
            yield update_step
        finally:
            # Update final status
            progress.update(task_id, description=f"{operation_name} - {current_step}")


class RenderStepOutput:
    """A clean, unified interface for CLI operation rendering with steps and output.

    This class replaces the clunky pattern of using render_quick_start_guide(),
    operation_context(), and create_steps_from_names() separately.

    Usage:
        # Simple operation with steps
        renderer = RenderStepOutput(console, "Creating cluster", ["Validate", "Deploy", "Configure"])
        with renderer:
            # Step 1
            renderer.advance("Validate")
            # ... do validation ...

            # Step 2
            renderer.advance("Deploy")
            # ... do deployment ...

            # Step 3
            renderer.advance("Configure")
            # ... do configuration ...

        # Optional quick start guide
        renderer.show_quick_start()
    """

    def __init__(
        self,
        console: Console,
        operation_name: str,
        step_names: Optional[List[str]] = None,
        verbose: bool = False,
        use_panel: bool = False,
        use_single_panel: bool = False,
        show_start_message: bool = True,
        command_start_time: Optional[float] = None,
        json_output: bool = False,
    ):
        """Initialize the renderer.

        Args:
            console: Rich console for output
            operation_name: Name of the operation
            step_names: Optional list of step names
            verbose: Whether to enable verbose output
            use_panel: Whether to use panel-style progress (vs simple progress)
            use_single_panel: Whether to use a single updating panel instead of multiple steps
            show_start_message: Whether to show start message when no steps
            command_start_time: Start time of the command for accurate timing
            json_output: Whether to output in JSON format instead of rich rendering
        """
        self.console = console
        self.operation_name = operation_name
        self.verbose = verbose
        self.use_panel = use_panel
        self.use_single_panel = use_single_panel
        self.show_start_message = show_start_message
        self.command_start_time = command_start_time
        self.json_output = json_output

        # Create Step objects from names
        self.steps = []
        if step_names:
            self.steps = [Step(name) for name in step_names]

        # Internal state
        self._context_manager = None
        self._advance_function = None
        self._entered = False

    def _call_advance_function(self, step_name: str, status: str, show_final: bool = False):
        """Safely call the advance function with the right number of parameters."""
        if not self._advance_function:
            return

        # Try with 3 parameters first (panel version), then fallback to 2 (steps version)
        try:
            self._advance_function(step_name, status, show_final)  # type: ignore
        except TypeError:
            # Fallback for functions that only take 2 parameters
            self._advance_function(step_name, status)  # type: ignore

    def __enter__(self):
        """Enter the context manager."""
        self._entered = True

        # If JSON output mode, suppress all visual output
        if self.json_output:
            return self

        if self.steps:
            # Check if we should use the single updating panel
            if self.use_single_panel:
                self._context_manager = single_progress_panel(
                    operation_name=self.operation_name,
                    console=self.console,
                    command_start_time=self.command_start_time,
                )
                self._advance_function = self._context_manager.__enter__()
            else:
                # Use progress context managers directly
                title = self.operation_name
                final_message = f"{self.operation_name} completed successfully!"

                if self.use_panel:
                    self._context_manager = progress_with_panel(
                        steps=self.steps,
                        console=self.console,
                        verbose=self.verbose,
                        title=title,
                        panel_title=f"{self.operation_name} Progress",
                        final_message=final_message,
                        command_start_time=self.command_start_time,
                    )
                else:
                    self._context_manager = progress_with_steps(
                        steps=self.steps,
                        console=self.console,
                        verbose=self.verbose,
                        title=title,
                        command_start_time=self.command_start_time,
                    )
                self._advance_function = self._context_manager.__enter__()
        else:
            # Simple context without steps
            if self.verbose or self.show_start_message:
                self.console.print(f"[blue]ℹ[/blue] Starting {self.operation_name}...")

        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> Optional[bool]:
        """Exit the context manager."""
        # If JSON output mode, suppress all visual output
        if self.json_output:
            self._entered = False
            return False

        if self._context_manager:
            result = self._context_manager.__exit__(exc_type, exc_val, exc_tb)
        else:
            # Simple context completion message
            if self.verbose or self.show_start_message:
                if exc_type is None:
                    self.console.print(f"[green]✓[/green] {self.operation_name} completed")
                else:
                    self.console.print(f"[red]✗[/red] {self.operation_name} failed")
            result = False

        self._entered = False
        return result

    def advance(
        self, step_name: Optional[str] = None, status: str = "completed", show_final: bool = False
    ):
        """Advance to the next step or update current step status.

        Args:
            step_name: Name of the step (optional if using sequential advancement)
            status: Status to set ("starting", "completed", "failed", "warning")
            show_final: Whether to show final completion message
        """
        if not self._entered:
            raise RuntimeError("RenderStepOutput must be used as a context manager")

        # If JSON output mode, suppress all visual output
        if self.json_output:
            return

        if self._advance_function:
            # Use wrapper to handle different function signatures
            if step_name:
                self._call_advance_function(step_name, status, show_final)
            else:
                self._call_advance_function("", status, show_final)
        else:
            # Simple logging when no steps defined
            if step_name and self.verbose:
                if status == "starting":
                    self.console.print(f"[blue]ℹ[/blue] {step_name}...")
                elif status == "completed":
                    self.console.print(f"[green]✓[/green] {step_name}")
                elif status == "failed":
                    self.console.print(f"[red]✗[/red] {step_name}")
                elif status == "warning":
                    self.console.print(f"[yellow]⚠[/yellow] {step_name}")

    def start_step(self, step_name: str):
        """Start a step."""
        self.advance(step_name, "starting")

    def complete_step(self, step_name: str):
        """Complete a step."""
        self.advance(step_name, "completed")

    def fail_step(self, step_name: str):
        """Fail a step."""
        self.advance(step_name, "failed")

    def warn_step(self, step_name: str):
        """Mark a step with warning."""
        self.advance(step_name, "warning")

    def panel_step(self, panel: Panel):
        """Display a Rich panel within the renderer context.

        This allows commands to easily display panels consistently using the
        same console instance as the renderer.

        Args:
            panel: Rich Panel object to display
        """
        if not self._entered:
            raise RuntimeError("RenderStepOutput must be used as a context manager")

        # If JSON output mode, suppress panel output
        if self.json_output:
            return

        self.console.print(panel)

    def table_step(self, table: Table):
        """Display a Rich table within the renderer context.

        This allows commands to easily display tables consistently using the
        same console instance as the renderer.

        Args:
            table: Rich Table object to display
        """
        if not self._entered:
            raise RuntimeError("RenderStepOutput must be used as a context manager")

        # If JSON output mode, suppress table output
        if self.json_output:
            return

        self.console.print(table)

    def show_quick_start(self):
        """Show the quick start guide."""
        # If JSON output mode, suppress quick start guide
        if self.json_output:
            return

        message = snick.dedent(
            """
            • To view cluster details, use the command: vantage clusters get

            • To create a new cluster, use the command: vantage clusters create --help

            • For more information on any command run it with the --help option.

            • To check all the available commands, refer to: vantage --help
            """
        ).strip()

        panel = Panel(
            message,
            title="[bold magenta]Quick Start Guide for Vantage-CLI[/bold magenta]",
            border_style="blue",
            expand=False,
        )

        self.console.print()
        self.console.print(panel)

    @classmethod
    def json_bypass(cls, data: Any):
        """Render JSON output and bypass all step tracking.

        Use this when json_output=True to skip the entire progress system.
        """
        render_json(data)

    @classmethod
    def simple_operation(cls, console: Console, operation_name: str, verbose: bool = False):
        """Create a simple renderer without steps for basic operations.

        Args:
            console: Rich console for output
            operation_name: Name of the operation
            verbose: Whether to enable verbose output

        Returns:
            RenderStepOutput configured for simple operation
        """
        return cls(
            console=console,
            operation_name=operation_name,
            step_names=None,
            verbose=verbose,
            show_start_message=True,
        )


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


class Step:
    """Represents a single operation step that can be used across all commands."""

    def __init__(
        self,
        name: str,
        duration_estimate: Optional[float] = None,
        action: Optional[Callable[..., Any]] = None,
    ):
        """Initialize an operation step.

        Args:
            name: Human-readable name for the step
            duration_estimate: Estimated duration in seconds (optional)
            action: Callable to execute for this step (optional)
        """
        self.name = name
        self.duration_estimate = duration_estimate
        self.action = action


@contextmanager
def progress_with_steps(
    steps: List[Step],
    console: Console,
    verbose: bool = False,
    title: str = "Processing...",
    command_start_time: Optional[float] = None,
):
    """Context manager for operation progress visualization with step-by-step progress.

    Args:
        steps: List of operation steps to execute
        console: Rich console for output
        verbose: Whether to show detailed logging
        title: Overall title for the operation
        command_start_time: Start time of the command for accurate timing

    Yields:
        A function to advance to the next step
    """
    if verbose:
        # In verbose mode, just yield a simple function that logs the step
        def advance_step(step_name: str, status: str = "completed"):
            if status == "starting":
                console.print(f"[blue]ℹ[/blue] {step_name}...")
            elif status == "completed":
                console.print(f"[green]✓[/green] {step_name}")
            elif status == "failed":
                console.print(f"[red]✗[/red] {step_name}")
            elif status == "warning":
                console.print(f"[yellow]⚠[/yellow] {step_name}")

        yield advance_step
        return

    # Non-verbose mode: use progress bar/spinner
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        CommandTimeElapsedColumn(command_start_time),
        console=console,
        transient=False,
    ) as progress:
        # Create a task for the overall operation
        main_task = progress.add_task(title, total=len(steps))
        current_step = 0

        def advance_step(step_name: str, status: str = "completed"):
            nonlocal current_step

            if status == "starting":
                # Update the current step description
                progress.update(main_task, description=f"{title} - {step_name}")
            elif status in ["completed", "failed", "warning"]:
                # Advance to next step
                current_step += 1
                progress.update(main_task, advance=1)

                if current_step < len(steps):
                    # Show next step if available
                    next_step = steps[current_step]
                    progress.update(main_task, description=f"{title} - {next_step.name}")
                else:
                    # All steps completed
                    if status == "completed":
                        progress.update(main_task, description=f"{title} - Complete!")
                    elif status == "failed":
                        progress.update(main_task, description=f"{title} - Failed!")

        yield advance_step


def _create_verbose_advance_function(console: Console, final_message: str):
    """Create advance function for verbose mode."""

    def advance_step(step_name: str, status: str = "completed", show_final: bool = False):
        if status == "starting":
            console.print(f"[blue]ℹ[/blue] {step_name}...")
        elif status == "completed":
            console.print(f"[green]✓[/green] {step_name}")
        elif status == "failed":
            console.print(f"[red]✗[/red] {step_name}")
        elif status == "warning":
            console.print(f"[yellow]⚠[/yellow] {step_name}")

        if show_final:
            console.print(Panel(final_message, title="Complete"))

    return advance_step


def _create_progress_table(steps: List[Step], step_statuses: List[str]) -> Table:
    """Create a table showing the current progress of all steps."""
    table = Table(show_header=False, show_edge=False, padding=(0, 1))
    table.add_column("Status", width=3)
    table.add_column("Step", style="")

    for i, step in enumerate(steps):
        status_icon = step_statuses[i]
        step_name = step.name

        # Style based on status
        if status_icon == "✓":
            style = "green"
        elif status_icon == "✗":
            style = "red"
        elif status_icon == "⚠":
            style = "yellow"
        else:
            style = "blue"

        table.add_row(status_icon, step_name, style=style)

    return table


def _create_panel(steps: List[Step], step_statuses: List[str], panel_title: str) -> Panel:
    """Create the live panel with current progress."""
    progress_table = _create_progress_table(steps, step_statuses)
    return Panel(progress_table, title=panel_title)


def _update_step_status(
    step_name: str, status: str, steps: List[Step], step_statuses: List[str], current_step: int
) -> int:
    """Update step status and return updated current_step."""
    if status == "starting":
        # Find the step and update its status to spinner
        for i, step in enumerate(steps):
            if step.name == step_name:
                step_statuses[i] = "⠋"
                return i
    elif status == "completed":
        # Mark current step as completed with spinner
        if current_step < len(step_statuses):
            step_statuses[current_step] = "⠋"
    elif status == "failed":
        # Mark current step as failed
        if current_step < len(step_statuses):
            step_statuses[current_step] = "✗"
    elif status == "warning":
        # Mark current step as warning
        if current_step < len(step_statuses):
            step_statuses[current_step] = "⚠"

    return current_step


@contextmanager
def progress_with_panel(
    steps: List[Step],
    console: Console,
    verbose: bool = False,
    title: str = "Processing...",
    panel_title: str = "Progress",
    final_message: str = "Operation completed successfully!",
    command_start_time: Optional[float] = None,
):
    """Context manager for operation progress visualization with live panels.

    Args:
        steps: List of operation steps to execute
        console: Rich console for output
        verbose: Whether to show detailed logging
        title: Overall title for the operation
        panel_title: Title for the progress panel
        final_message: Message to show when operation completes
        command_start_time: Start time of the command for accurate timing

    Yields:
        A function to advance to the next step
    """
    if verbose:
        # In verbose mode, just yield a simple function that logs the step
        yield _create_verbose_advance_function(console, final_message)
        return

    # Non-verbose mode: use live panel with progress visualization
    current_step = 0
    step_statuses = ["⠋"] * len(steps)  # Initialize with spinner

    with Live(
        _create_panel(steps, step_statuses, panel_title), console=console, refresh_per_second=10
    ) as live:

        def advance_step(step_name: str, status: str = "completed", show_final: bool = False):
            nonlocal current_step

            current_step = _update_step_status(
                step_name, status, steps, step_statuses, current_step
            )

            # Update the live panel
            if show_final:
                # Show final completion panel
                live.update(Panel(final_message, title=f"{panel_title} - Complete!"))
            else:
                live.update(_create_panel(steps, step_statuses, panel_title))

        yield advance_step


@contextmanager
def simple_spinner(message: str, console: Console, verbose: bool = False):
    """Display a simple spinner for single operations.

    Args:
        message: Message to display
        console: Rich console for output
        verbose: Whether to show detailed logging (if True, just prints the message)
    """
    if verbose:
        console.print(f"[blue]ℹ[/blue] {message}...")
        yield
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task(message, total=None)
        yield


def log_verbose(console: Console, message: str, verbose: bool, level: str = "info"):
    """Log a message only if verbose mode is enabled.

    Args:
        console: Rich console for output
        message: Message to log
        verbose: Whether verbose mode is enabled
        level: Log level (info, success, warning, error)
    """
    if not verbose:
        return

    if level == "info":
        console.print(f"[blue]ℹ[/blue] {message}")
    elif level == "success":
        console.print(f"[green]✓[/green] {message}")
    elif level == "warning":
        console.print(f"[yellow]⚠[/yellow] {message}")
    elif level == "error":
        console.print(f"[red]✗[/red] {message}")


def log_always(console: Console, message: str, level: str = "info"):
    """Log a message that should always be shown.

    Args:
        console: Rich console for output
        message: Message to log
        level: Log level (info, success, warning, error)
    """
    if level == "info":
        console.print(f"[blue]ℹ[/blue] {message}")
    elif level == "success":
        console.print(f"[green]✓[/green] {message}")
    elif level == "warning":
        console.print(f"[yellow]⚠[/yellow] {message}")
    elif level == "error":
        console.print(f"[red]✗[/red] {message}")


def show_operation_result(
    console: Console, operation: str, success: bool, message: str = "", verbose: bool = False
):
    """Show the result of an operation with consistent formatting.

    Args:
        console: Rich console for output
        operation: Name of the operation (e.g., "Deployment", "Cluster creation")
        success: Whether the operation was successful
        message: Additional message to show
        verbose: Whether verbose mode is enabled
    """
    if success:
        status_icon = "[green]✓[/green]"
        status_text = "successful"
    else:
        status_icon = "[red]✗[/red]"
        status_text = "failed"

    result_message = f"{status_icon} {operation} {status_text}"
    if message:
        result_message += f": {message}"

    console.print(result_message)


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
    console.print_json(json.dumps(data))


class TerminalOutputManager:
    """A simple, generic class for managing terminal output during operations with a Live panel.

    This class provides a clean interface for terminal output using a Rich Live panel
    that captures all operation messages and displays them in real-time within a panel.
    It can be easily used by any command that needs to display operation results.

    Usage:
        with TerminalOutputManager(console, "Deploying Application") as output:
            output.info("Setting up configuration...")
            output.success("Configuration complete")
            output.warning("Some warnings occurred")
            output.error("An error occurred")
            # Final panel automatically displays with all messages
    """

    def __init__(
        self,
        console: Console,
        operation_name: str,
        verbose: bool = False,
        json_output: bool = False,
        use_live_panel: bool = True,
    ):
        """Initialize the terminal output manager.

        Args:
            console: Rich console for output
            operation_name: Name of the operation being performed
            verbose: Whether to enable verbose output
            json_output: Whether to suppress output for JSON mode
            use_live_panel: Whether to use live panel (True) or simple output (False)
        """
        self.console = console
        self.operation_name = operation_name
        self.verbose = verbose
        self.json_output = json_output
        self.use_live_panel = use_live_panel
        self._started = False
        self._finished = False
        self._messages: List[str] = []
        self._live: Optional[Live] = None
        self._current_status = "Starting..."
        self._panel_border_style = "blue"
        self._panel_title_style = "blue"

    def __enter__(self):
        """Enter the context manager and start the live panel if enabled."""
        if self.json_output:
            return self

        self._started = True

        if self.use_live_panel:
            # Start with initial panel
            self._update_panel()
            self._live = Live(
                self._create_panel(), console=self.console, refresh_per_second=4, transient=False
            )
            self._live.__enter__()
        else:
            # Simple mode - just print start message
            self.console.print(f"[blue]ℹ[/blue] Starting {self.operation_name}...")

        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> bool:
        """Exit the context manager and finalize the panel."""
        if self.json_output:
            return False

        self._finished = True

        if self.use_live_panel and self._live:
            # Update panel with final status
            if exc_type is None:
                self._current_status = "✓ Complete"
            else:
                self._current_status = "✗ Failed"

            self._update_panel()
            self._live.__exit__(exc_type, exc_val, exc_tb)
        else:
            # Simple mode completion message
            if exc_type is None:
                self.console.print(f"[green]✓[/green] {self.operation_name} completed")
            else:
                self.console.print(f"[red]✗[/red] {self.operation_name} failed")

        return False

    def _create_panel(self) -> Panel:
        """Create the live panel with current messages and status."""
        if not self._messages:
            content = f"[dim]Starting {self.operation_name}...[/dim]"
        else:
            content = "\n".join(self._messages)

        # Add current status at the bottom if present
        if self._current_status:
            content += f"\n\n[bold]{self._current_status}[/bold]"

        return Panel(
            content,
            title=f"[{self._panel_title_style}]{self.operation_name}[/{self._panel_title_style}]",
            border_style=self._panel_border_style,
            padding=(1, 2),
            width=120,
        )

    def _update_panel(self):
        """Update the live panel if it's active."""
        if self.use_live_panel and self._live and self._started:
            self._live.update(self._create_panel())

    def _add_message(self, message: str, icon: str = "", style: str = ""):
        """Add a message to the panel and update display."""
        if self.json_output:
            return

        formatted_message = f"{icon} {message}" if icon else message
        if style:
            formatted_message = f"[{style}]{formatted_message}[/{style}]"

        self._messages.append(formatted_message)

        if self.use_live_panel:
            self._update_panel()
        else:
            # In simple mode, print immediately
            self.console.print(formatted_message)

    def start(self, message: Optional[str] = None) -> None:
        """Start the operation and display initial message.

        Args:
            message: Optional custom start message
        """
        if self.json_output:
            return

        start_msg = message or f"Starting {self.operation_name}..."
        self._current_status = start_msg

        if self.use_live_panel:
            self._update_panel()
        else:
            self.console.print(f"[blue]ℹ[/blue] {start_msg}")

    def info(self, message: str) -> None:
        """Display an informational message.

        Args:
            message: Information message to display
        """
        if self.json_output or (not self.verbose and self.use_live_panel):
            return

        self._add_message(message, "ℹ", "blue")

    def success(self, message: str) -> None:
        """Display a success message.

        Args:
            message: Success message to display
        """
        if self.json_output:
            return

        self._add_message(message, "✓", "green")

    def warning(self, message: str) -> None:
        """Display a warning message.

        Args:
            message: Warning message to display
        """
        if self.json_output:
            return

        self._add_message(message, "⚠", "yellow")

    def error(self, message: str) -> None:
        """Display an error message.

        Args:
            message: Error message to display
        """
        if self.json_output:
            return

        self._add_message(message, "✗", "red")

    def status(self, message: str) -> None:
        """Update the current status without adding to message history.

        Args:
            message: Status message to display
        """
        if self.json_output:
            return

        self._current_status = message

        if self.use_live_panel:
            self._update_panel()
        else:
            self.console.print(f"[dim]{message}[/dim]")

    def finish(self, message: Optional[str] = None, success: bool = True) -> None:
        """Finish the operation and display final message.

        Args:
            message: Optional custom finish message
            success: Whether the operation was successful
        """
        if self.json_output:
            return

        if message:
            if success:
                self._add_message(message, "✓", "green")
            else:
                self._add_message(message, "✗", "red")

        # Update final status
        if success:
            self._current_status = "✓ Operation completed successfully"
        else:
            self._current_status = "✗ Operation failed"

        if self.use_live_panel:
            self._update_panel()

    def set_final_content(self, content: str, success: bool = True) -> None:
        """Set final content to display in the live panel instead of separate status.

        Args:
            content: Final content to display
            success: Whether the operation was successful (affects border color)
        """
        if self.json_output:
            return

        # Clear existing messages and status, replace with final content
        self._messages = [content]
        self._current_status = ""  # No additional status when showing final content

        if self.use_live_panel:
            # Update the panel title and border style based on success
            self._panel_border_style = "green" if success else "red"
            self._panel_title_style = "green" if success else "red"
            self._update_panel()

    def display_final_panel(self, content: str, title: str = "Operation Complete") -> None:
        """Display a final panel with operation results after the live panel ends.

        Args:
            content: Content to display in the panel
            title: Title for the panel
        """
        if self.json_output:
            return

        # Only show final panel if we're not already using live panel
        # (live panel will show the results)
        if not self.use_live_panel:
            panel = Panel(
                content, title=f"[green]{title}[/green]", padding=(1, 2), border_style="green"
            )
            self.console.print()
            self.console.print(panel)

    def print(self, message: str, style: Optional[str] = None) -> None:
        """Print a message directly to console (outside the panel).

        Args:
            message: Message to print
            style: Optional Rich style to apply
        """
        if self.json_output:
            return

        if self.use_live_panel:
            # Add to panel messages
            if style:
                self._add_message(f"[{style}]{message}[/{style}]")
            else:
                self._add_message(message)
        else:
            # Print directly
            if style:
                self.console.print(message, style=style)
            else:
                self.console.print(message)


class UniversalOutputFormatter:
    """Universal output formatter for all CLI commands.

    This class provides a centralized way to format and display data from all commands,
    supporting both JSON output and rich table formatting. It automatically detects
    data structure and creates appropriate tables.

    Usage:
        formatter = UniversalOutputFormatter(console, json_output=ctx.obj.json_output)
        formatter.output(data, title="Job Scripts")
    """

    def __init__(self, console: Console, json_output: bool = False):
        """Initialize the output formatter.

        Args:
            console: Rich console for output
            json_output: Whether to output JSON instead of formatted tables
        """
        self.console = console
        self.json_output = json_output

    def _get_terminal_width(self) -> int:
        """Retrieve the current terminal width and update the console accordingly."""
        fallback_width = max(getattr(self.console, "width", 80) or 80, 40)

        try:
            terminal_size = shutil.get_terminal_size(fallback=(fallback_width, 20))
            width = max(terminal_size.columns, 40)
        except (OSError, ValueError):  # pragma: no cover - rare environments
            width = fallback_width

        if width != getattr(self.console, "width", width):
            # Update the console so downstream Rich components honor the latest size
            self.console.width = width

        return width

    def output(self, data: Any, title: str = "", empty_message: str = "No items found.") -> None:
        """Output data either as JSON or formatted table.

        Args:
            data: Data to output (dict, list, or simple value)
            title: Title for the table display
            empty_message: Message to show when data is empty
        """
        if self.json_output:
            self._output_json(data)
        else:
            self._output_table(data, title, empty_message)

    def _output_json(self, data: Any) -> None:
        """Output data as formatted JSON without syntax highlighting.

        We disable highlighting to ensure clean JSON output that can be piped
        to tools like jq without ANSI color codes interfering.
        """
        if data is None:
            self.console.print_json("{}", highlight=False)
        else:
            self.console.print_json(json.dumps(data, indent=2), highlight=False)

    def _output_table(self, data: Any, title: str, empty_message: str) -> None:
        """Output data as a formatted table."""
        if not data:
            self.console.print(f"📋 {empty_message}", style="yellow")
            return

        # Handle different data types
        if isinstance(data, dict):
            if "items" in data and isinstance(data["items"], list):
                # Paginated response format
                self._render_list_as_table(data["items"], title)
                self._render_pagination_info(data)
            else:
                # Single item
                self._render_dict_as_table(data, title or "Details")
        elif isinstance(data, list):
            if len(data) == 0:
                self.console.print(f"📋 {empty_message}", style="yellow")
            else:
                self._render_list_as_table(data, title)
        else:
            # Simple value
            self.console.print(data)

    def _render_list_as_table(self, items: List[Dict[str, Any]], title: str) -> None:
        """Render a list of items as a table using Textual's auto-layout principles."""
        if not items:
            return

        # For now, use enhanced Rich table with Textual-inspired auto-layout
        # This maintains compatibility while preparing for full Textual integration
        self._render_textual_style_table(items, title)

    def _render_textual_style_table(self, items: List[Dict[str, Any]], title: str) -> None:
        """Render table using proper Textual DataTable implementation."""
        if not items:
            return

        # Use actual Textual DataTable for proper formatting
        try:
            self._render_with_textual_datatable(items, title)
        except Exception as e:
            # If Textual fails, show a simple error message
            self.console.print(f"[red]Error rendering table: {e}[/red]")

    def _render_with_textual_datatable(self, items: List[Dict[str, Any]], title: str) -> None:
        """Render using Rich Table with dynamic width based on terminal size."""
        from rich import box
        from rich.table import Table

        if not items:
            return

        # Get terminal width for dynamic sizing
        terminal_width = self._get_terminal_width()

        # Get all unique keys from items
        all_keys = set()
        for item in items:
            all_keys.update(item.keys())

        # Sort keys with priority fields first
        common_fields = [
            "id",
            "name",
            "title",
            "description",
            "status",
            "created_at",
            "updated_at",
        ]
        sorted_keys = []

        for field in common_fields:
            if field in all_keys:
                sorted_keys.append(field)
                all_keys.remove(field)

        sorted_keys.extend(sorted(all_keys))

        # Calculate dynamic column widths based on terminal size
        column_widths = self._calculate_proportional_widths(items, sorted_keys, terminal_width)

        # Create Rich table with proper formatting and dynamic sizing
        table = Table(
            title=title if title else None,
            show_header=True,
            header_style="bold magenta",
            box=box.ROUNDED,
            border_style="blue",
            padding=(0, 1),
            expand=True,
            width=terminal_width,
        )

        # Add columns with calculated widths and smart overflow handling
        # Track which columns use ellipsis for smart truncation
        column_overflow = {}

        for key in sorted_keys:
            header = self._format_column_header(key)
            col_width = column_widths.get(key, 20)

            # Determine overflow strategy based on column type and width
            if key.lower() in ["description", "summary", "details", "message"]:
                # Long text fields - use fold for wrapping when very narrow
                if col_width < 20:
                    overflow = "ellipsis"
                    no_wrap = True
                else:
                    overflow = "fold"
                    no_wrap = False
            elif key.lower() in ["id", "client_id", "clientid", "deployment_id", "product_id"]:
                # IDs should never wrap, always use ellipsis
                overflow = "ellipsis"
                no_wrap = True
            elif "_at" in key.lower() or "date" in key.lower() or "time" in key.lower():
                # Dates/times should not wrap
                overflow = "ellipsis"
                no_wrap = True
            else:
                # Default columns - use ellipsis for narrow columns, fold for wider ones
                if col_width < 15:
                    overflow = "ellipsis"
                    no_wrap = True
                else:
                    overflow = "fold"
                    no_wrap = False

            column_overflow[key] = (overflow, col_width)

            table.add_column(
                header, overflow=overflow, no_wrap=no_wrap, width=col_width, max_width=col_width
            )

        # Add rows with smart truncation for ellipsis columns
        for item in items:
            row_data = []
            for key in sorted_keys:
                value = item.get(key, "")
                formatted_value = self._format_cell_value(key, value)

                # Apply smart truncation for columns using ellipsis
                overflow_type, col_width = column_overflow[key]
                if overflow_type == "ellipsis" and isinstance(formatted_value, str):
                    formatted_value = self._smart_truncate(formatted_value, col_width)

                row_data.append(formatted_value)
            table.add_row(*row_data)

        # Print using our console
        self.console.print(table)

    def _calculate_proportional_widths(
        self, items: List[Dict[str, Any]], sorted_keys: List[str], total_width: int
    ) -> Dict[str, int]:
        """Calculate proportional column widths with intelligent auto-scaling.

        This method implements a smart column width algorithm that:
        1. Calculates actual content widths from data
        2. Assigns priority to important columns (id, name, status)
        3. Scales down gracefully when terminal width is limited
        4. Hides less important columns if necessary for very narrow terminals
        """
        if not items or not sorted_keys:
            return {}

        # Reserve space for borders, padding, and separators
        # Each column needs: 1 char padding left + 1 char padding right + 1 char separator = 3 chars
        border_overhead = (len(sorted_keys) * 3) + 4  # +4 for outer borders
        available_width = max(40, total_width - border_overhead)  # Minimum 40 chars usable width

        # Calculate actual content widths by sampling data
        actual_widths = {}
        for key in sorted_keys:
            # Start with header width
            header_width = len(self._format_column_header(key))
            max_content_width = header_width

            # Sample up to 10 items to get realistic content width
            sample_size = min(10, len(items))
            for item in items[:sample_size]:
                value = item.get(key, "")
                formatted_value = self._format_cell_value(key, value)
                content_width = len(str(formatted_value))
                max_content_width = max(max_content_width, content_width)

            actual_widths[key] = max_content_width

        # Define column priorities and constraints
        column_config = self._get_column_config(sorted_keys, actual_widths)

        # Calculate minimum required width
        min_required = sum(config["min_width"] for config in column_config.values())

        # If we don't have enough space, we need to be more aggressive
        if min_required > available_width:
            # Use even smaller minimum widths
            for key in sorted_keys:
                if column_config[key]["priority"] <= 1:
                    # Low priority - can be very narrow or hidden
                    column_config[key]["min_width"] = 4
                elif column_config[key]["priority"] == 2:
                    # Medium priority - minimal width
                    column_config[key]["min_width"] = 6
                else:
                    # High priority - keep reasonable minimum
                    column_config[key]["min_width"] = 8

        # Calculate final widths using priority-based allocation
        final_widths = self._allocate_column_widths(sorted_keys, column_config, available_width)

        return final_widths

    def _get_column_config(
        self, sorted_keys: List[str], actual_widths: Dict[str, int]
    ) -> Dict[str, Dict[str, Any]]:
        """Get column configuration with priorities and constraints based on actual content."""
        config = {}

        for key in sorted_keys:
            key_lower = key.lower()
            actual_width = actual_widths[key]

            # Determine priority (3=high, 2=medium, 1=low, 0=can hide)
            if key_lower in ["id", "name", "title", "status"]:
                priority = 3  # Always show
            elif key_lower in [
                "description",
                "created_at",
                "updated_at",
                "owner_email",
                "email",
            ]:
                priority = 2  # Show if possible
            elif key_lower in ["client_id", "cloned_from_id", "parent_template_id"]:
                priority = 1  # Low priority
            else:
                priority = 2  # Default medium priority

            # Determine optimal and maximum widths BASED ON ACTUAL CONTENT
            # Use actual_width as the primary guide, with sensible constraints
            if key_lower == "id":
                # IDs: prefer showing full UUID (36 chars) but can compress
                optimal = min(actual_width + 2, 38)  # +2 for padding
                max_width = 40
                min_width = 10
            elif key_lower in ["name", "title"]:
                optimal = min(actual_width + 2, 40)
                max_width = 50
                min_width = 15
            elif key_lower in ["description", "message", "details", "summary"]:
                optimal = min(actual_width + 2, 50)
                max_width = 60
                min_width = 20
            elif key_lower in ["status", "state"]:
                # Status: fit to content (usually short)
                optimal = min(actual_width + 2, 15)
                max_width = 15
                min_width = 8
            elif "_at" in key_lower or "date" in key_lower or "time" in key_lower:
                # Timestamps: fit to actual format
                optimal = min(actual_width + 2, 20)
                max_width = 22
                min_width = 12
            elif "email" in key_lower:
                optimal = min(actual_width + 2, 30)
                max_width = 40
                min_width = 15
            elif "_name" in key_lower or "cluster" in key_lower or "app" in key_lower:
                # Names: fit to content, usually shorter
                optimal = min(actual_width + 2, 25)
                max_width = 30
                min_width = 8
            elif "provider" in key_lower or "substrate" in key_lower:
                # Providers: usually short (aws, gcp, localhost, etc.)
                optimal = min(actual_width + 2, 15)
                max_width = 20
                min_width = 10
            else:
                # Default: fit to content with reasonable bounds
                optimal = min(actual_width + 2, 25)
                max_width = 35
                min_width = 8

            config[key] = {
                "priority": priority,
                "actual_width": actual_width,
                "optimal_width": optimal,
                "max_width": max_width,
                "min_width": min_width,
            }

        return config

    def _assign_minimum_widths(
        self,
        sorted_keys: List[str],
        column_config: Dict[str, Dict[str, Any]],
        available_width: int,
    ) -> tuple[Dict[str, int], int]:
        """Assign minimum widths to all columns.

        Returns:
            Tuple of (final_widths dict, remaining_width)
        """
        final_widths = {}
        remaining_width = available_width
        for key in sorted_keys:
            min_width = column_config[key]["min_width"]
            final_widths[key] = min_width
            remaining_width -= min_width
        return final_widths, remaining_width

    def _distribute_by_priority(
        self,
        sorted_keys: List[str],
        column_config: Dict[str, Dict[str, Any]],
        final_widths: Dict[str, int],
        remaining_width: int,
    ) -> int:
        """Distribute space by priority levels (3, 2, 1).

        Returns:
            Updated remaining width
        """
        for priority_level in [3, 2, 1]:
            if remaining_width <= 0:
                break

            high_priority_keys = [
                k for k in sorted_keys if column_config[k]["priority"] == priority_level
            ]

            if not high_priority_keys:
                continue

            # Calculate how much each column wants to grow
            growth_needed = {}
            total_growth = 0
            for key in high_priority_keys:
                current = final_widths[key]
                optimal = column_config[key]["optimal_width"]
                growth = max(0, optimal - current)
                growth_needed[key] = growth
                total_growth += growth

            if total_growth == 0:
                continue

            # Distribute available space proportionally
            space_to_distribute = min(remaining_width, total_growth)

            for key in high_priority_keys:
                if total_growth > 0:
                    proportion = growth_needed[key] / total_growth
                    extra_width = int(space_to_distribute * proportion)
                    final_widths[key] += extra_width
                    remaining_width -= extra_width

        return remaining_width

    def _distribute_remaining_evenly(
        self,
        sorted_keys: List[str],
        column_config: Dict[str, Dict[str, Any]],
        final_widths: Dict[str, int],
        remaining_width: int,
    ) -> None:
        """Distribute any remaining space evenly among columns that can grow."""
        keys_can_grow = [k for k in sorted_keys if final_widths[k] < column_config[k]["max_width"]]

        while remaining_width > 0 and keys_can_grow:
            extra_per_column = max(1, remaining_width // len(keys_can_grow))

            for key in keys_can_grow[:]:
                max_width = column_config[key]["max_width"]
                current = final_widths[key]

                if current >= max_width:
                    keys_can_grow.remove(key)
                    continue

                can_add = min(extra_per_column, max_width - current, remaining_width)
                final_widths[key] += can_add
                remaining_width -= can_add

                if final_widths[key] >= max_width:
                    keys_can_grow.remove(key)

            if extra_per_column == 0:
                break

    def _allocate_column_widths(
        self,
        sorted_keys: List[str],
        column_config: Dict[str, Dict[str, Any]],
        available_width: int,
    ) -> Dict[str, int]:
        """Allocate column widths using priority-based algorithm."""
        # Start by assigning minimum widths
        final_widths, remaining_width = self._assign_minimum_widths(
            sorted_keys, column_config, available_width
        )

        if remaining_width <= 0:
            # No extra space available, use minimums
            return final_widths

        # Distribute remaining space by priority
        remaining_width = self._distribute_by_priority(
            sorted_keys, column_config, final_widths, remaining_width
        )

        # If there's still space left, distribute evenly among all columns up to their max
        if remaining_width > 0:
            self._distribute_remaining_evenly(
                sorted_keys, column_config, final_widths, remaining_width
            )

        return final_widths

    def _render_dict_as_table(self, item: Dict[str, Any], title: str) -> None:
        """Render a single dictionary as a details table with auto-scaling."""
        from rich import box

        # Get terminal width for dynamic sizing
        terminal_width = self._get_terminal_width()

        # Calculate column widths (30% for field name, 70% for value)
        field_width = max(15, int(terminal_width * 0.3))
        value_width = max(30, int(terminal_width * 0.7) - 10)  # Reserve space for borders

        table = Table(
            title=f"📋 {title}",
            show_header=True,
            header_style="bold magenta",  # Match list table header style
            box=box.ROUNDED,
            border_style="blue",
            expand=True,
            width=terminal_width,
        )
        table.add_column("Field", style="cyan", no_wrap=True, width=field_width)
        table.add_column("Value", style="white", overflow="fold", no_wrap=False, width=value_width)

        # Sort keys with common ones first
        common_fields = [
            "id",
            "name",
            "title",
            "description",
            "status",
            "created_at",
            "updated_at",
        ]
        sorted_keys = []

        for field in common_fields:
            if field in item:
                sorted_keys.append(field)

        # Add remaining fields
        remaining = [k for k in sorted(item.keys()) if k not in common_fields]
        sorted_keys.extend(remaining)

        for key in sorted_keys:
            header = self._format_column_header(key)
            value = self._format_cell_value(key, item[key])
            table.add_row(header, value)

        self.console.print(table)

    def _render_pagination_info(self, data: Dict[str, Any]) -> None:
        """Render pagination information if available."""
        if all(key in data for key in ["page", "pages", "total"]):
            page_info = f"Page {data['page']} of {data['pages']} (Total: {data['total']})"
            self.console.print(f"\n{page_info}", style="dim")

    def _format_column_header(self, key: str) -> str:
        """Format a column header nicely."""
        # Handle common abbreviations and special cases
        special_cases = {
            "id": "ID",
            "api": "API",
            "url": "URL",
            "json": "JSON",
            "xml": "XML",
            "html": "HTML",
            "http": "HTTP",
            "https": "HTTPS",
            "ip": "IP",
            "cpu": "CPU",
            "gpu": "GPU",
            "ram": "RAM",
            "os": "OS",
            "ui": "UI",
            "cli": "CLI",
            "db": "DB",
        }

        # Split on underscores and capitalize each word
        words = key.lower().split("_")
        formatted_words = []

        for word in words:
            if word in special_cases:
                formatted_words.append(special_cases[word])
            else:
                formatted_words.append(word.capitalize())

        return " ".join(formatted_words)

    def _get_column_style(self, key: str) -> str:
        """Get appropriate style for a column based on its key."""
        if key.lower() in ["id"]:
            return "cyan"
        elif key.lower() in ["name", "title"]:
            return "green"
        elif key.lower() in ["status", "state"]:
            return "yellow"
        elif key.lower().endswith("_at") or "date" in key.lower() or "time" in key.lower():
            return "blue"
        elif key.lower() in ["description"]:
            return "white"
        else:
            return "white"

    def _get_column_max_width(self, key: str) -> int:
        """Get maximum width for a column based on its key to prevent wrapping."""
        key_lower = key.lower()

        # Field-specific width limits
        if key_lower == "id":
            return 15
        elif key_lower in ["name", "title"]:
            return 25
        elif key_lower == "description":
            return 40
        elif key_lower in ["status", "state"]:
            return 12
        elif key_lower.endswith("_at") or "date" in key_lower or "time" in key_lower:
            return 12
        elif key_lower in ["email", "url", "endpoint"]:
            return 30
        elif key_lower in ["region", "zone", "location"]:
            return 15
        elif key_lower in ["cidr", "ip", "subnet"]:
            return 18
        else:
            # Default max width for unknown fields
            return 20

    def _get_field_max_length(self, key: str) -> int:
        """Get maximum character length for a field value to prevent wrapping."""
        # This should match the column max width minus some padding for table borders
        return self._get_column_max_width(key)

    def _get_field_priority_weight(self, key: str) -> float:
        """Get priority weight for field type to determine column width allocation.

        Higher weight = wider column in proportional distribution.
        """
        key_lower = key.lower()

        # High priority fields (get more space)
        if key_lower in ["description", "message", "details"]:
            return 3.0
        elif key_lower in ["name", "title"]:
            return 2.0
        elif key_lower in ["email", "url", "endpoint"]:
            return 2.0

        # Medium priority fields
        elif key_lower in ["id"]:
            return 1.5
        elif key_lower.endswith("_at") or "date" in key_lower or "time" in key_lower:
            return 1.5
        elif key_lower in ["region", "zone", "location", "cidr", "ip", "subnet"]:
            return 1.5

        # Low priority fields (get less space)
        elif key_lower in ["status", "state"]:
            return 1.0
        elif key_lower in ["is_archived", "archived", "enabled", "active"]:
            return 0.8

        # Default weight
        else:
            return 1.2

    def _get_adaptive_max_width(self, key: str, num_columns: int) -> int:
        """Get adaptive maximum width for a column based on terminal size and column count.

        This allows Rich to auto-size columns while preventing excessive width.

        Args:
            key: Column key
            num_columns: Total number of columns in the table

        Returns:
            Maximum width for this column
        """
        # Get actual terminal width
        import os
        import shutil

        env_columns = os.environ.get("COLUMNS")
        if env_columns and env_columns.isdigit():
            terminal_width = int(env_columns)
        else:
            terminal_width = shutil.get_terminal_size().columns

        # Use a reasonable range: min 80, max 200
        terminal_width = min(200, max(80, terminal_width))

        # Calculate average column width (accounting for borders and padding)
        available_width = terminal_width - (num_columns + 1) - (num_columns * 2)
        avg_width = available_width // num_columns if num_columns > 0 else 20

        # Adjust based on field type and terminal size
        key_lower = key.lower()

        if terminal_width >= 160:
            # Wide terminal - be more generous
            if key_lower in ["description", "message", "details"]:
                return min(60, avg_width * 2)
            elif key_lower in ["name", "title", "email", "url"]:
                return min(40, avg_width + 10)
            elif key_lower in ["id"]:
                return min(20, avg_width)
            else:
                return min(30, avg_width + 5)

        elif terminal_width >= 120:
            # Medium terminal - moderate constraints
            if key_lower in ["description", "message", "details"]:
                return min(40, avg_width + 10)
            elif key_lower in ["name", "title"]:
                return min(25, avg_width + 5)
            elif key_lower in ["email", "url"]:
                return min(30, avg_width + 5)
            elif key_lower in ["id"]:
                return min(15, avg_width)
            else:
                return min(20, avg_width)

        else:
            # Narrow terminal - tight constraints
            if key_lower in ["description", "message", "details"]:
                return min(25, avg_width + 5)
            elif key_lower in ["name", "title"]:
                return min(20, avg_width)
            elif key_lower in ["id"]:
                return min(12, avg_width - 2)
            elif key_lower in ["status", "state"]:
                return min(10, avg_width - 2)
            else:
                return min(15, avg_width)

    def _smart_truncate(self, text: str, max_width: int) -> str:
        """Intelligently truncate text to fit within max_width.

        For very narrow columns (< 6 chars), shows first 3 chars + "..."
        For wider columns, uses standard ellipsis truncation.

        Args:
            text: Text to truncate
            max_width: Maximum width for the text

        Returns:
            Truncated text with ellipsis if needed
        """
        if not text or len(text) <= max_width:
            return text

        # For very narrow columns (< 6 chars), show first 3 chars + "..."
        if max_width < 6:
            # Ensure we have at least 4 chars for "X..." pattern
            if max_width >= 4:
                return text[: max_width - 3] + "..."
            else:
                # For extremely narrow (1-3 chars), just show what we can
                return text[:max_width]

        # For columns 6+ chars, use standard truncation with ellipsis
        return text[: max_width - 3] + "..."

    def _format_cell_value(self, key: str, value: Any) -> str:
        """Format a cell value for display."""
        if value is None:
            return "N/A"
        elif value == "":
            return "N/A"
        elif isinstance(value, bool):
            return "[green]✓[/green]" if value else "[red]✗[/red]"
        elif isinstance(value, (list, dict)):
            # For complex nested data, show a summary
            if isinstance(value, list):
                return f"[{len(value)} items]" if value else "[]"
            else:
                return f"[{len(value)} keys]" if value else "{}"
        elif isinstance(value, str):
            # Handle common formatting cases
            if key.lower().endswith("_at") or "date" in key.lower():
                # Try to format dates nicely, fallback to original
                try:
                    from datetime import datetime

                    if "T" in value and value.endswith("Z"):
                        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                        return dt.strftime("%Y-%m-%d")
                    return value
                except Exception:
                    return value
            elif key.lower() in ["status", "state"]:
                return value.upper()
            else:
                # Let Rich handle text layout with ratio-based column sizing and 150-char width
                # No manual truncation needed - Rich will handle overflow properly
                return value
        else:
            return str(value)

    def success(self, message: str) -> None:
        """Display a success message."""
        if not self.json_output:
            self.console.print(f"✅ {message}", style="green")

    def error(self, message: str) -> None:
        """Display an error message."""
        if not self.json_output:
            self.console.print(f"❌ {message}", style="red")

    def warning(self, message: str) -> None:
        """Display a warning message."""
        if not self.json_output:
            self.console.print(f"⚠️ {message}", style="yellow")

    def info(self, message: str) -> None:
        """Display an info message."""
        if not self.json_output:
            self.console.print(f"ℹ️ {message}", style="blue")

    # ============================================================================
    # CRUD Operation Render Functions
    # ============================================================================

    def render_list(
        self, data: Any, resource_name: str, empty_message: Optional[str] = None
    ) -> None:
        """Render a list of resources (for LIST operations).

        Args:
            data: Response data containing list of items
            resource_name: Human-readable name for the resource type (e.g., "Job Scripts")
            empty_message: Custom message when no items found
        """
        if empty_message is None:
            empty_message = f"No {resource_name.lower()} found."

        self.output(data, title=resource_name, empty_message=empty_message)

    def render_get(self, data: Any, resource_name: str, resource_id: str = "") -> None:
        """Render a single resource (for GET operations).

        Args:
            data: Response data for the single resource
            resource_name: Human-readable name for the resource type
            resource_id: ID of the resource being displayed
        """
        if self.json_output:
            self._output_json(data)
        else:
            title = f"{resource_name}"
            if resource_id:
                title += f" (ID: {resource_id})"

            if isinstance(data, dict):
                self._render_dict_as_table(data, title)
            else:
                self.console.print(f"📄 {title}")
                self.console.print(data)

    def render_create(
        self, data: Any, resource_name: str, success_message: Optional[str] = None
    ) -> None:
        """Render result of resource creation (for CREATE operations).

        Args:
            data: Response data from creation
            resource_name: Human-readable name for the resource type
            success_message: Custom success message
        """
        if self.json_output:
            self._output_json(data)
        else:
            if success_message is None:
                resource_id = ""
                if isinstance(data, dict) and "id" in data:
                    resource_id = f" (ID: {data['id']})"
                success_message = f"{resource_name} created successfully{resource_id}"

            self.success(success_message)

            # Show key details of created resource
            if isinstance(data, dict) and data:
                self.console.print("\n📋 Created Resource Details:")
                self._render_dict_as_table(data, "")

    def render_update(
        self,
        data: Any,
        resource_name: str,
        resource_id: str = "",
        success_message: Optional[str] = None,
    ) -> None:
        """Render result of resource update (for UPDATE operations).

        Args:
            data: Response data from update
            resource_name: Human-readable name for the resource type
            resource_id: ID of the updated resource
            success_message: Custom success message
        """
        if self.json_output:
            self._output_json(data)
        else:
            if success_message is None:
                id_part = f" (ID: {resource_id})" if resource_id else ""
                success_message = f"{resource_name} updated successfully{id_part}"

            self.success(success_message)

            # Show updated resource details
            if isinstance(data, dict) and data:
                self.console.print("\n📋 Updated Resource Details:")
                self._render_dict_as_table(data, "")

    def render_delete(
        self,
        resource_name: str,
        resource_id: str = "",
        success_message: Optional[str] = None,
        data: Any = None,
    ) -> None:
        """Render result of resource deletion (for DELETE operations).

        Args:
            resource_name: Human-readable name for the resource type
            resource_id: ID of the deleted resource
            success_message: Custom success message
            data: Optional response data from deletion
        """
        if self.json_output and data is not None:
            self._output_json(data)
        else:
            if success_message is None:
                id_part = f" (ID: {resource_id})" if resource_id else ""
                success_message = f"{resource_name} deleted successfully{id_part}"

            self.success(success_message)

    def render_error(self, error_message: str, details: Any = None) -> None:
        """Render error information for any failed operation.

        Args:
            error_message: Main error message
            details: Optional additional error details
        """
        if self.json_output:
            error_data = {"error": error_message}
            if details:
                error_data["details"] = details
            self._output_json(error_data)
        else:
            self.error(error_message)
            if details and isinstance(details, dict):
                self.console.print("\n📋 Error Details:")
                self._render_dict_as_table(details, "")
            elif details:
                self.console.print(f"\nDetails: {details}")

    def render_confirmation(
        self, message: str, resource_name: str = "", resource_id: str = ""
    ) -> None:
        """Render confirmation prompts for destructive operations.

        Args:
            message: Confirmation message
            resource_name: Human-readable name for the resource type
            resource_id: ID of the resource being affected
        """
        if not self.json_output:
            if resource_name and resource_id:
                self.console.print(f"🗑️  {resource_name} (ID: {resource_id})")
            self.console.print(f"⚠️  {message}", style="yellow bold")

    def render_operation_status(
        self, operation: str, resource_name: str, status: str, details: str = ""
    ) -> None:
        """Render status of long-running operations.

        Args:
            operation: Type of operation (e.g., "Deployment", "Migration")
            resource_name: Human-readable name for the resource
            status: Current status (e.g., "In Progress", "Completed", "Failed")
            details: Additional status details
        """
        if self.json_output:
            status_data = {
                "operation": operation,
                "resource": resource_name,
                "status": status,
                "details": details,
            }
            self._output_json(status_data)
        else:
            status_style = {
                "completed": "green",
                "success": "green",
                "in progress": "yellow",
                "pending": "yellow",
                "failed": "red",
                "error": "red",
            }.get(status.lower(), "blue")

            self.console.print(f"🔄 {operation} - {resource_name}")
            self.console.print(f"Status: {status}", style=status_style)
            if details:
                self.console.print(f"Details: {details}")

    def render_bulk_operation(
        self, operation: str, results: Dict[str, Any], resource_name: str
    ) -> None:
        """Render results of bulk operations affecting multiple resources.

        Args:
            operation: Type of bulk operation (e.g., "Bulk Delete", "Bulk Update")
            results: Dictionary with success/failure counts and details
            resource_name: Human-readable name for the resource type
        """
        if self.json_output:
            self._output_json(results)
        else:
            total = results.get("total", 0)
            success = results.get("success", 0)
            failed = results.get("failed", 0)

            self.console.print(f"📊 {operation} - {resource_name}")
            self.console.print(f"Total processed: {total}")
            if success > 0:
                self.console.print(f"✅ Successful: {success}", style="green")
            if failed > 0:
                self.console.print(f"❌ Failed: {failed}", style="red")

            # Show detailed results if available
            if "details" in results and isinstance(results["details"], list):
                self.console.print("\n📋 Detailed Results:")
                for detail in results["details"]:
                    if isinstance(detail, dict):
                        status_icon = "✅" if detail.get("success") else "❌"
                        resource_id = detail.get("id", "Unknown")
                        message = detail.get("message", "")
                        self.console.print(f"{status_icon} ID {resource_id}: {message}")

    def render_validation_results(self, validation_results: Dict[str, Any]) -> None:
        """Render validation results for data validation operations.

        Args:
            validation_results: Dictionary containing validation results
        """
        if self.json_output:
            self._output_json(validation_results)
        else:
            is_valid = validation_results.get("valid", False)
            errors = validation_results.get("errors", [])
            warnings = validation_results.get("warnings", [])

            if is_valid:
                self.success("Validation successful")
            else:
                self.error("Validation failed")

            if errors:
                self.console.print("\n❌ Validation Errors:")
                for error in errors:
                    self.console.print(f"  • {error}", style="red")

            if warnings:
                self.console.print("\n⚠️  Validation Warnings:")
                for warning in warnings:
                    self.console.print(f"  • {warning}", style="yellow")
