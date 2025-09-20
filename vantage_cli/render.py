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


# Keep DeploymentStep for backward compatibility
DeploymentStep = Step


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


# Keep old function names for backward compatibility
deployment_progress = progress_with_steps
deployment_progress_panel = progress_with_panel


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
