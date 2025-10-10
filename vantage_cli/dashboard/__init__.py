#!/usr/bin/env python3
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
"""Modular CLI Dashboard Package

A reusable Textual-based dashboard class for Vantage CLI Dashboard functionality.
"""

import asyncio
import inspect
import signal
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, cast

import typer
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    Button,
    DataTable,
    Header,
    ProgressBar,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
)

from vantage_cli.apps.utils import get_available_apps
from vantage_cli.exceptions import Abort
from vantage_cli.sdk.admin.management.organizations import get_extra_attributes
from vantage_cli.sdk.cluster import cluster_sdk
from .cluster_management_tab_pane import ClusterManagementTabPane
from .dependency_tracker import DependencyTracker, Worker, WorkerState
from .deployment_management_tab_pane import DeploymentManagementTabPane
from .profile_management_tab_pane import ProfileManagementTabPane

if TYPE_CHECKING:
    from vantage_cli.sdk.cluster.schema import Cluster


@dataclass
class DashboardConfig:
    """Configuration for the dashboard"""

    title: str = "Production Dashboard"
    subtitle: str = "Real-time worker execution with scrollable logs"
    enable_stats: bool = True
    enable_logs: bool = True
    enable_controls: bool = True
    enable_clusters: bool = True
    refresh_interval: float = 0.5


@dataclass
class ServiceConfig:
    """Configuration for a service in the dashboard"""

    name: str
    url: str
    emoji: str = "🔧"
    dependencies: Optional[List[str]] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class CustomHeader(Header):
    """Custom header that extends the built-in Header."""

    pass


class DashboardApp(App):
    """Modular production dashboard that can be configured and reused"""

    BINDINGS = [
        ("ctrl+c,q", "quit", "Quit"),
        ("ctrl+d", "toggle_dark", "Toggle Dark Mode"),
        ("r", "restart", "Restart Execution"),
        ("l", "clear_logs", "Clear Logs"),
        ("tab", "next_tab", "Next Tab"),
    ]

    CSS = """
    .section-header {
        text-style: bold;
        color: $accent;
        margin: 1;
    }
    
    .stats-container {
        height: 10;
        border: solid $success;
    }
    
    .log-container {
        border: solid $warning;
    }
    
    #activity-log {
        height: 100%;
        scrollbar-gutter: stable;
    }
    
    /* Worker progress group - proportional scaling (equal) */
    #worker-progress-group {
        height: 1fr;
        min-height: 8;
        border: heavy magenta;
        border-title-color: magenta;
        border-title-style: bold;
        padding: 1;
        overflow: auto;
    }
    
    #full-logs {
        height: 100%;
        scrollbar-gutter: stable;
    }
    
    DataTable {
        height: auto;
    }
    
    Button {
        margin: 1;
    }
    
    /* Service status group - proportional scaling (medium) */
    #service-status-group {
        height: 1fr;
        min-height: 6;
        border: heavy magenta;
        border-title-color: magenta;
        border-title-style: bold;
        padding: 1;
        overflow: auto;
    }
    
    /* Activity log wrapper - proportional scaling (dominant) */
    #activity-log-wrapper {
        height: 3fr;
        min-height: 10;
        border: heavy cyan;
        border-title-color: cyan;
        border-title-style: bold;
        padding: 0;
        overflow: auto;
    }
    
    /* Deployment details group - proportional scaling (medium) */
    #deployment-details-group {
        height: 1fr;
        min-height: 6;
        border: heavy magenta;
        border-title-color: magenta;
        border-title-style: bold;
        padding: 1;
        overflow: auto;
    }
    
    /* Vantage Platform panel - proportional scaling (moderate) */
    #vantage-platform {
        height: 2fr;
        min-height: 8;
        border: heavy ansi_bright_green;
        border-title-color: ansi_bright_green;
        border-title-style: bold;
        padding: 1;
        overflow: auto;
    }
    
    /* Footer styling - original working version */
    #footer {
        height: 3;
        background: $surface-lighten-1;
        border-top: solid $primary;
        content-align: center middle;
        text-style: dim;
        dock: bottom;
    }
    
    /* Main panel spacing handled by parent containers */
    
    /* URL link styling */
    .url-link {
        color: cyan;
        text-style: italic;
    }
    
    /* RichLog inside wrapper - fill container */
    #activity-log {
        border: none;
        height: 100%;
        width: 100%;
    }
    
    /* Main panel fills the tab content area */
    #main-panel {
        height: 1fr;
        layout: horizontal;
    }
    
    /* Left content area - coordinated auto-layout */
    #left-content {
        width: 60%;
        height: 100%;
        layout: vertical;
        overflow: hidden;
    }
    
    /* Right content area - coordinated auto-layout */
    #right-content {
        width: 40%;
        height: 100%;
        min-width: 30;
        layout: vertical;
        overflow: hidden;
    }
    
    /* Force the horizontal container to fill space */
    #activity-log-wrapper > Horizontal {
        height: 100%;
        min-height: 25;
    }
    
    /* Main content fills available space in vertical stack */
    #main-content {
        height: 1fr;
        width: 100%;
    }
    
    /* TabbedContent fills the main content area */
    TabbedContent {
        width: 100%;
        height: 100%;
    }
    
    /* Control buttons positioned to the right */
    #control-buttons {
        width: auto;
        min-width: 20;
        dock: right;
        padding: 1;
        background: $surface-lighten-1;
        border-left: solid $primary;
        content-align: center top;
    }
    
    /* Style control buttons to look like tabs */
    .tab-button {
        width: 18;
        height: 3;
        margin: 0 1 1 0;
        border: solid $primary;
        background: $panel;
        text-align: center;
    }
    
    .tab-button:hover {
        background: $panel-lighten-1;
        border: solid $accent;
    }
    
    /* Responsive section headers - white on dark, black on light */
    .section-header {
        text-style: bold;
        color: $text;
        margin: 1;
    }
    
    /* Vertical stacking layout - let containers stack naturally */
    Screen {
        layout: vertical;
    }
    
    /* Main content should fill available space above footer */
    #tab-and-buttons-container {
        height: 1fr;
    }
    
    /* Footer docks at bottom naturally */
    #footer {
        height: 3;
        dock: bottom;
    }
    
    /* Remove unnecessary margins */
    TabPane {
        padding: 1;
    }
    
    .log-container {
        margin-bottom: 1;
    }
    """

    def __init__(
        self,
        config: Optional[DashboardConfig] = None,
        services: Optional[List[ServiceConfig]] = None,
        custom_handlers: Optional[Dict[str, Callable[..., Any]]] = None,
        platform_info: Optional[Dict[str, str]] = None,
        ctx: Optional[typer.Context] = None,
    ):
        super().__init__()

        # Configuration
        self.config = config or DashboardConfig()
        self.services = services or self._get_default_services()
        self.custom_handlers = custom_handlers or {}
        self.platform_info = platform_info or self._get_default_platform_info()
        self.ctx = ctx
        self.cli_ctx = ctx
        self.available_apps = get_available_apps()
        self.selected_app_key: Optional[str] = None
        self.app_table: Optional[DataTable[Any]] = None
        self.app_row_mapping: Dict[str, int] = {}
        self.cluster_input: Optional[Input] = None

        # Set app title and subtitle
        self.TITLE = self.config.title
        self.SUB_TITLE = self.config.subtitle

        # Create workers from services
        self.worker_list = self._create_workers_from_services()
        self.tracker = DependencyTracker(self.worker_list)

        # Runtime state
        self.start_time = time.time()
        self.execution_complete = False
        self.execution_running = False

    def _get_default_services(self) -> List[ServiceConfig]:
        """Get default service configuration"""
        return [
            ServiceConfig("cert-manager", "https://cert-mgr.k8s.local", "🔧"),
            ServiceConfig("prometheus", "https://prometheus.monitoring.local", "📊"),
            ServiceConfig(
                "slinky", "https://slinky.api.local", "🔗", ["cert-manager", "prometheus"]
            ),
            ServiceConfig("slurm", "https://slurm.scheduler.local", "⚡", ["slinky"]),
            ServiceConfig("jupyterhub", "https://jupyter.notebooks.local", "🚀", ["slurm"]),
        ]

    def _get_default_platform_info(self) -> Dict[str, str]:
        """Get default platform information"""
        return {
            "name": "Vantage Compute",
            "cluster_url": "https://app.vantagecompute.ai/clusters/<cluster-id>",
            "notebooks_url": "https://app.vantagecompute.ai/notebooks",
            "docs_url": "https://docs.vantagecompute.ai/platform/deployment-applications",
            "support_email": "support@vantagecompute.ai",
        }

    def _create_workers_from_services(self) -> List[Worker]:
        """Create Worker objects from ServiceConfig list"""
        workers = []
        for service in self.services:
            # Use custom handler if provided, otherwise use dummy handler
            def _default_handler(worker_id: str, *, duration: float = 1.0) -> Dict[str, Any]:
                return {"duration": duration}

            handler = self.custom_handlers.get(service.name, _default_handler)
            worker = Worker(service.name, handler, WorkerState.INIT, service.dependencies)
            workers.append(worker)
        return workers

    def _suggest_cluster_name(self, app_key: str) -> str:
        base = app_key.replace("/", "-")
        return f"{base}-cluster"

    def _populate_app_table(self) -> None:
        if not self.app_table or not self.available_apps:
            return

        if self.app_row_mapping:
            return

        rows = sorted(self.available_apps.items(), key=lambda item: item[0])

        for index, (app_key, app_info) in enumerate(rows):
            module = app_info.get("module")
            module_name = getattr(module, "__name__", "unknown") if module else "unknown"
            summary = "No description available"
            create_function = app_info.get("create_function")
            if create_function and getattr(create_function, "__doc__", None):
                summary = create_function.__doc__.strip().split("\n")[0]

            self.app_table.add_row(app_key, module_name, summary, key=app_key)
            self.app_row_mapping[app_key] = index

    def _select_default_app(self) -> None:
        if not self.available_apps or not self.app_table:
            return

        first_key = next(iter(sorted(self.available_apps)))
        self.selected_app_key = first_key

        try:
            self.app_table.focus()
            select_row = getattr(self.app_table, "select_row", None)
            if callable(select_row):
                select_row(first_key)
        except Exception:
            index = self.app_row_mapping.get(first_key)
            if index is not None:
                try:
                    setattr(self.app_table, "cursor_coordinate", (index, 0))
                except Exception:
                    pass

        self._update_cluster_input(first_key, force=True)

    def _update_cluster_input(self, app_key: str, force: bool = False) -> None:
        if not self.cluster_input:
            return

        if force or not self.cluster_input.value.strip():
            self.cluster_input.value = self._suggest_cluster_name(app_key)

    def _get_cluster_name(self) -> str:
        if self.cluster_input is None:
            return ""
        return self.cluster_input.value.strip()

    def _build_command_invocation(
        self,
        command: Callable[..., Any],
        app_key: str,
        cluster_name: Optional[str],
    ) -> Tuple[List[Any], Dict[str, Any]]:
        if self.cli_ctx is None:
            raise ValueError("CLI context is unavailable for command execution.")

        signature = inspect.signature(command)
        parameters = list(signature.parameters.values())
        if not parameters:
            raise ValueError("Command has no parameters to bind.")

        args: List[Any] = [self.cli_ctx]
        kwargs: Dict[str, Any] = {}

        for param in parameters[1:]:
            if param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue

            if param.name in {"cluster_name", "deployment_id"}:
                if not cluster_name:
                    raise ValueError(f"{param.name.replace('_', ' ')} is required.")
                if param.kind in (
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ):
                    args.append(cluster_name)
                else:
                    kwargs[param.name] = cluster_name
            elif param.name == "app_name":
                if param.kind in (
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ):
                    args.append(app_key)
                else:
                    kwargs[param.name] = app_key
            elif param.name == "dev_run":
                kwargs[param.name] = False
            elif param.name == "force":
                kwargs[param.name] = True
            elif param.default is inspect.Signature.empty:
                raise ValueError(
                    f"Unsupported parameter '{param.name}' for {command.__name__}."
                )

        return args, kwargs

    async def _perform_app_action(
        self,
        action: str,
        app_key: str,
        cluster_name: Optional[str],
    ) -> None:
        app_info = self.available_apps.get(app_key)
        if not app_info:
            self.add_log(f"❌ Application '{app_key}' is not available", "ERROR")
            return

        module = app_info.get("module")
        if module is None:
            self.add_log(f"❌ Module for '{app_key}' is not loaded", "ERROR")
            return

        command_name = f"{action}_command"
        command = getattr(module, command_name, None)
        if command is None:
            self.add_log(f"⚠️ {action.title()} not supported for '{app_key}'", "WARNING")
            return

        try:
            args, kwargs = self._build_command_invocation(command, app_key, cluster_name)
            self.add_log(f"⏳ Running {action} for '{app_key}'", "INFO")
            await command(*args, **kwargs)
            self.add_log(f"✅ {action.title()} completed for '{app_key}'", "SUCCESS")
        except typer.Exit as exit_exc:
            if exit_exc.exit_code == 0:
                self.add_log(f"✅ {action.title()} completed for '{app_key}'", "SUCCESS")
            else:
                self.add_log(
                    f"⚠️ {action.title()} exited with code {exit_exc.exit_code} for '{app_key}'",
                    "ERROR",
                )
        except Exception as exc:  # pragma: no cover - defensive
            self.add_log(f"💥 {action.title()} failed for '{app_key}': {exc}", "ERROR")

    def _trigger_app_action(self, action: str) -> None:
        if not self.selected_app_key:
            self.add_log("⚠️ Select an application before performing actions", "WARNING")
            return

        cluster_name = self._get_cluster_name()
        if action in {"create", "remove"} and not cluster_name:
            self.add_log("⚠️ Provide a cluster name for this action", "WARNING")
            return

        asyncio.create_task(
            self._perform_app_action(action, self.selected_app_key, cluster_name or None)
        )

    def compose(self) -> ComposeResult:
        """Create the dashboard layout"""
        yield CustomHeader()

        with Horizontal(id="tab-and-buttons-container"):
            with TabbedContent(initial="main", id="main-content"):
                with TabPane("📊 Dashboard", id="main"):
                    with Vertical():
                        with Horizontal(id="main-panel"):
                            # Left side: Worker progress
                            with Vertical(id="left-content"):
                                yield Static("� Applications", classes="section-header")
                                app_table_raw = DataTable(
                                    id="app-table",
                                    show_header=True,
                                    cursor_type="row",
                                    zebra_stripes=True,
                                )
                                app_table_raw.add_columns("Application", "Module", "Summary")
                                app_table = cast(DataTable[Any], app_table_raw)
                                self.app_table = app_table
                                yield app_table

                                yield Static("�📈 Worker Progress", classes="section-header")
                                with Vertical(id="worker-progress-group"):
                                    for service in self.services:
                                        yield Static(f"{service.emoji} {service.name}")
                                        yield ProgressBar(total=100, id=f"progress-{service.name}")

                            # Right side: Activity log and platform info
                            with Vertical(id="right-content"):
                                yield Static("📜 Activity Log", classes="section-header")
                                with Vertical(id="activity-log-wrapper"):
                                    with Horizontal():
                                        yield RichLog(
                                            id="activity-log", auto_scroll=True, markup=True
                                        )

                                yield Static(
                                    f"🚀 {self.platform_info['name']}", classes="section-header"
                                )
                                with Vertical(id="vantage-platform"):
                                    yield Static("[bold]🔗 Access your cluster[/bold]")
                                    yield Static(
                                        f"    {self.platform_info['cluster_url']}",
                                        classes="url-link",
                                    )
                                    yield Static("")
                                    yield Static("[bold]📓 Create a notebook[/bold]")
                                    yield Static(
                                        f"    {self.platform_info['notebooks_url']}",
                                        classes="url-link",
                                    )
                                    yield Static("")
                                    yield Static("[bold]📚 Documentation[/bold]")
                                    yield Static(
                                        f"    {self.platform_info['docs_url']}", classes="url-link"
                                    )
                                    yield Static("")
                                    yield Static("[bold]💬 Support[/bold]")
                                    yield Static(
                                        f"    {self.platform_info['support_email']}",
                                        classes="url-link",
                                    )

                if self.config.enable_logs:
                    with TabPane("📜 Full Logs", id="logs-tab"):
                        yield Static("📜 Complete Activity History", classes="section-header")
                        yield RichLog(id="full-logs", auto_scroll=True, markup=True)
                        with Horizontal():
                            yield Button("📤 Export Logs", id="export-btn")
                            yield Button("🧹 Clear All", id="clear-all-btn", variant="error")

                if self.config.enable_stats:
                    with TabPane("📊 System Stats", id="stats-tab"):
                        yield Static("💻 System Information", classes="section-header")
                        yield Static("CPU Usage: 0%", id="cpu-stat")
                        yield Static("Memory: 0%", id="memory-stat")
                        yield Static("Runtime: 0s", id="runtime-stat")
                        yield Static("Workers Active: 0", id="active-stat")
                        yield Static("Completed: 0", id="completed-stat")
                        yield Static("Failed: 0", id="failed-stat")

                # Add cluster management tab if enabled and context is available
                if self.config.enable_clusters and self.ctx:
                    yield ClusterManagementTabPane(self.ctx)

                # Add profile management tab if context is available
                if self.ctx:
                    yield ProfileManagementTabPane(self.ctx)

                # Add deployment management tab if context is available
                if self.ctx:
                    yield DeploymentManagementTabPane(self.ctx)

            # Control buttons
            if self.config.enable_controls:
                with Vertical(id="control-buttons"):
                    yield Static("⚙️ Deployment Controls", classes="section-header")
                    cluster_input = Input(
                        placeholder="cluster-name",
                        id="cluster-name-input",
                    )
                    self.cluster_input = cluster_input
                    yield cluster_input
                    yield Button("Create", id="create-btn", variant="success", classes="tab-button")
                    yield Button("Status", id="status-btn", variant="primary", classes="tab-button")
                    yield Button("Remove", id="remove-btn", variant="error", classes="tab-button")

        # Footer
        yield Static(
            f"🚀 {self.platform_info['name']} - {self.config.title} | Press Ctrl+C to quit",
            id="footer",
        )

    def on_mount(self):
        """Initialize the dashboard"""
        self.add_log(f"🎯 {self.config.title} initialized")
        self.add_log("💡 Use Ctrl+C or 'q' to quit, 'r' to restart")

        self.setup_tables()
        self._populate_app_table()
        self._select_default_app()

        if self.config.enable_stats:
            self.set_interval(self.config.refresh_interval, self.refresh_stats)

    def setup_tables(self):
        """Set up the data tables"""
        # No deployment tables needed - they're handled by the deployment management tab pane
        pass

    def add_log(self, message: str, level: str = "INFO"):
        """Add a message to log widgets"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {"SUCCESS": "green", "ERROR": "red", "WARNING": "yellow", "INFO": "blue"}
        color = colors.get(level, "white")

        formatted_message = f"[{color}][{timestamp}] {message}[/{color}]"

        try:
            activity_log = self.query_one("#activity-log", RichLog)
            activity_log.write(formatted_message)

            if self.config.enable_logs:
                full_log = self.query_one("#full-logs", RichLog)
                full_log.write(formatted_message)
        except Exception:
            pass

    def refresh_stats(self):
        """Update system statistics"""
        if not hasattr(self, "tracker"):
            return

        try:
            import psutil

            runtime = time.time() - self.start_time

            # Count worker states
            states = {"active": 0, "completed": 0, "failed": 0}
            for worker in self.tracker.workers.values():
                if worker.state == WorkerState.IN_PROGRESS:
                    states["active"] += 1
                elif worker.state == WorkerState.COMPLETE:
                    states["completed"] += 1
                elif worker.state == WorkerState.FAILED:
                    states["failed"] += 1

            # Update stats widgets
            self.query_one("#cpu-stat", Static).update(f"CPU Usage: {psutil.cpu_percent():.1f}%")
            self.query_one("#memory-stat", Static).update(
                f"Memory: {psutil.virtual_memory().percent:.1f}%"
            )
            self.query_one("#runtime-stat", Static).update(f"Runtime: {runtime:.1f}s")
            self.query_one("#active-stat", Static).update(f"Workers Active: {states['active']}")
            self.query_one("#completed-stat", Static).update(f"Completed: {states['completed']}")
            self.query_one("#failed-stat", Static).update(f"Failed: {states['failed']}")

        except Exception:
            pass

    # Button event handlers
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = cast(DataTable[Any], event.data_table)

        if table.id != "app-table":
            return

        selected_key = str(event.row_key.value)
        self.selected_app_key = selected_key
        self._update_cluster_input(selected_key)
        self.add_log(f"🗂️ Selected application: {selected_key}", "INFO")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "create-btn":
            self._trigger_app_action("create")
        elif event.button.id == "status-btn":
            self._trigger_app_action("status")
        elif event.button.id == "remove-btn":
            self._trigger_app_action("remove")
        elif event.button.id == "start-btn":
            self.action_start_execution()
        elif event.button.id == "stop-btn":
            self.action_stop_execution()
        elif event.button.id == "restart-btn":
            self.action_restart()
        elif event.button.id == "clear-all-btn":
            self.action_clear_logs()
        elif event.button.id == "export-btn":
            self.action_export_logs()

    # Action methods
    def action_quit(self):
        """Handle quit action"""
        self.add_log("👋 Dashboard shutting down...", "INFO")
        self.exit()

    def action_toggle_dark(self):
        """Toggle dark mode"""
        self.dark = not self.dark
        mode = "dark" if self.dark else "light"
        self.add_log(f"🌓 Switched to {mode} mode", "INFO")

    def action_start_execution(self):
        """Start worker execution"""
        if not self.execution_running:
            self.add_log("🚀 Starting worker execution...", "SUCCESS")
            self.execution_running = True
            self.run_worker(self.execute_workers, exclusive=True)

    def action_stop_execution(self):
        """Stop worker execution"""
        if self.execution_running:
            self.add_log("⏹️ Stopping execution...", "WARNING")
            self.execution_running = False

    def action_restart(self):
        """Restart execution"""
        self.add_log("🔄 Restarting execution...", "INFO")
        for worker in self.worker_list:
            worker.state = WorkerState.INIT
        self.tracker = DependencyTracker(self.worker_list)

        for service in self.services:
            try:
                progress_bar = self.query_one(f"#progress-{service.name}", ProgressBar)
                progress_bar.update(progress=0)
            except Exception:
                pass

        self.execution_complete = False
        self.execution_running = False
        self.action_start_execution()

    def action_clear_logs(self):
        """Clear all logs"""
        try:
            self.query_one("#activity-log", RichLog).clear()
            if self.config.enable_logs:
                self.query_one("#full-logs", RichLog).clear()
            self.add_log("🧹 Logs cleared", "INFO")
        except Exception:
            pass

    def action_export_logs(self):
        """Export logs to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dashboard_logs_{timestamp}.txt"
        self.add_log(f"📤 Logs would be exported to {filename}", "SUCCESS")

    def action_next_tab(self):
        """Switch to next tab"""
        try:
            tabbed_content = self.query_one(TabbedContent)
            # Simple tab switching - you can enhance this
            self.add_log("🔄 Tab switched", "INFO")
        except Exception:
            pass

    async def execute_workers(self):
        """Execute workers with progress tracking"""
        self.add_log("📋 Starting execution", "INFO")

        for worker in self.worker_list:
            if not self.execution_running:
                break

            self.add_log(f"▶️ Processing {worker.id}...", "INFO")

            # Update worker state
            if hasattr(self, "tracker") and worker.id in self.tracker.workers:
                self.tracker.workers[worker.id].state = WorkerState.IN_PROGRESS

            # Update progress
            try:
                progress_bar = self.query_one(f"#progress-{worker.id}", ProgressBar)
                for progress in range(0, 101, 20):
                    if not self.execution_running:
                        break
                    progress_bar.update(progress=progress)
                    await asyncio.sleep(0.3)
            except Exception:
                pass

            # Complete worker
            if hasattr(self, "tracker") and worker.id in self.tracker.workers:
                self.tracker.workers[worker.id].state = WorkerState.COMPLETE

            self.add_log(f"✅ {worker.id} completed", "SUCCESS")

        self.add_log("🎉 All workers completed!", "SUCCESS")
        self.execution_running = False
        self.execution_complete = True


def run_dashboard(
    config: Optional[DashboardConfig] = None,
    services: Optional[List[ServiceConfig]] = None,
    custom_handlers: Optional[Dict[str, Callable[..., Any]]] = None,
    platform_info: Optional[Dict[str, str]] = None,
    ctx: Optional[typer.Context] = None,
    setup_signals: bool = True,
) -> None:
    """Run the dashboard with optional configuration.
    This is the main entry point for using the dashboard in your applications.
    """

    def signal_handler(signum: int, frame: Any) -> None:
        print(f"\\n👋 Dashboard interrupted by signal {signum}")
        sys.exit(0)

    if setup_signals:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    try:
        title = config.title if config else "Production Dashboard"
        print(f"🚀 Starting {title}...")
        print("💡 Use Ctrl+C to quit, or 'q' inside the app")

        app = DashboardApp(
            config=config,
            services=services,
            custom_handlers=custom_handlers,
            platform_info=platform_info,
            ctx=ctx,
        )
        app.run()

    except KeyboardInterrupt:
        print("\\n👋 Dashboard interrupted by user")
    except Exception as e:
        print(f"\\n💥 Dashboard error: {e}")
        sys.exit(1)
