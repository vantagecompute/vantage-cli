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

This dashboard integrates with the Vantage CLI SDK to provide real-time monitoring
and management of Vantage resources:

SDK Integration:
---------------
- **Clusters**: Uses `vantage_cli.sdk.cluster.schema.Cluster` for cluster data
- **Deployments**: Uses `vantage_cli.sdk.deployment.schema.Deployment` for deployment data  
- **Profiles**: Uses `vantage_cli.sdk.profile.schema.Profile` for profile management
- **Context**: Uses `vantage_cli.schemas.CliContext` for CLI execution context

Architecture:
------------
The dashboard uses a Worker/Service model for tracking deployment progress:
- `ServiceConfig`: Configuration for a tracked service (can be created from SDK objects)
- `Worker`: Execution unit that tracks state and dependencies
- `DependencyTracker`: Manages worker execution order based on dependencies

Tab Panes:
---------
- `ClusterManagementTabPane`: Manages clusters using cluster SDK
- `DeploymentManagementTabPane`: Manages deployments using deployment SDK
- `ProfileManagementTabPane`: Manages profiles using profile SDK

Example Usage:
-------------
```python
from vantage_cli.sdk.cluster import cluster_sdk
from vantage_cli.sdk.deployment import deployment_sdk
from vantage_cli.dashboard import DashboardConfig, ServiceConfig, run_dashboard

# Load data from SDK
clusters = await cluster_sdk.list_clusters(ctx)
deployments = await deployment_sdk.list(ctx)

# Convert SDK objects to services
services = [ServiceConfig.from_cluster(c) for c in clusters]
services += [ServiceConfig.from_deployment(d) for d in deployments]

# Configure and run dashboard
config = DashboardConfig(
    title="Vantage Dashboard",
    enable_stats=True,
    enable_logs=True,
    enable_clusters=True,
)

run_dashboard(config=config, services=services, ctx=ctx)
```
"""

import asyncio
import signal
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import typer
from rich.text import Text
from textual import work
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

from vantage_cli.auth import extract_persona, fetch_auth_tokens, is_token_expired
from vantage_cli.cache import clear_token_cache, load_tokens_from_cache
from vantage_cli.schemas import CliContext
from vantage_cli.sdk.cluster.schema import Cluster
from vantage_cli.sdk.deployment.schema import Deployment
from vantage_cli.sdk.profile.schema import Profile
from vantage_cli.sdk.profile import profile_sdk

from .cluster_management_tab_pane import ClusterManagementTabPane, CreateClusterModal, RemoveClusterModal
from .credential_management_tab_pane import CredentialManagementTabPane, CreateCredentialModal, RemoveCredentialModal
from .dependency_tracker import DependencyTracker, Worker, WorkerState
from .deployment_management_tab_pane import DeploymentManagementTabPane
from .login_modal import LoginModal
from .profile_management_tab_pane import ProfileManagementTabPane, CreateProfileModal, RemoveProfileModal


@dataclass
class DashboardConfig:
    """Configuration for the dashboard.
    
    This configures the dashboard behavior and which features are enabled.
    All tab panes that are enabled will use the SDK to fetch and display data.
    
    Attributes:
        title: Main title displayed in the header
        subtitle: Subtitle text for the header
        enable_stats: Enable the system statistics tab
        enable_logs: Enable the full logs tab
        enable_controls: Enable Create/Status/Remove control buttons
        enable_clusters: Enable cluster management tab (uses cluster SDK)
        refresh_interval: How often to refresh stats (in seconds)
        
    Example:
        ```python
        config = DashboardConfig(
            title="Production Clusters",
            enable_stats=True,
            enable_clusters=True,
            refresh_interval=1.0
        )
        ```
    """

    title: str = "Production Dashboard"
    subtitle: str = "Real-time worker execution with scrollable logs"
    enable_stats: bool = True
    enable_logs: bool = True
    enable_controls: bool = True
    enable_clusters: bool = True
    refresh_interval: float = 0.5


@dataclass
class ServiceConfig:
    """Configuration for a service in the dashboard.
    
    This represents a deployment service that can be tracked and monitored.
    Can be constructed from Cluster or Deployment SDK objects.
    """

    name: str
    url: str
    emoji: str = "🔧"
    dependencies: Optional[List[str]] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

    @classmethod
    def from_cluster(cls, cluster: Cluster) -> "ServiceConfig":
        """Create a ServiceConfig from a Cluster schema object."""
        provider_emoji_map = {
            "aws": "☁️",
            "gcp": "☁️",
            "azure": "☁️",
            "localhost": "💻",
            "maas": "🛠️",
            "on_prem": "🏢",
        }
        emoji = provider_emoji_map.get(cluster.provider.lower(), "🖥️")
        
        return cls(
            name=cluster.name,
            url=cluster.jupyterhub_url,
            emoji=emoji,
            dependencies=[],
        )

    @classmethod
    def from_deployment(cls, deployment: Deployment) -> "ServiceConfig":
        """Create a ServiceConfig from a Deployment schema object."""
        substrate_emoji_map = {
            "k8s": "🚢",
            "metal": "🔩",
            "vm": "🧱",
        }
        emoji = substrate_emoji_map.get(deployment.substrate.lower(), "🚀")
        
        dependencies = []
        if deployment.cluster:
            dependencies.append(deployment.cluster.name)
        
        return cls(
            name=f"{deployment.app_name}-{deployment.cluster.name}",
            url=deployment.vantage_cluster_ctx.base_api_url,
            emoji=emoji,
            dependencies=dependencies,
        )


class CustomHeader(Header):
    """Custom header that extends the built-in Header."""

    pass


class DashboardApp(App):
    """Modular production dashboard that can be configured and reused.
    
    This dashboard integrates with the Vantage CLI SDK to display and manage:
    - Clusters (via vantage_cli.sdk.cluster)
    - Deployments (via vantage_cli.sdk.deployment)
    - Profiles (via vantage_cli.sdk.profile)
    
    The dashboard uses Worker objects for tracking progress of service deployments
    and dependencies. Services can be created from Cluster or Deployment SDK objects
    using ServiceConfig.from_cluster() and ServiceConfig.from_deployment().
    
    Args:
        config: Dashboard configuration settings
        services: List of services to track (can be created from SDK objects)
        custom_handlers: Optional custom handlers for worker functions
        platform_info: Platform-specific information to display
        ctx: Typer context containing CLI context with SDK client configuration
    """

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
    
    /* Three horizontal panels inside left-content - each gets equal height */
    #deployments-panel {
        height: 1fr;
        layout: horizontal;
    }
    
    #clusters-panel {
        height: 1fr;
        layout: horizontal;
    }
    
    #apps-panel {
        height: 1fr;
        layout: horizontal;
    }
    
    /* List and details sections within each panel - 50/50 split */
    #deployments-list {
        width: 50%;
        height: 100%;
        padding: 0;
        border: solid $accent;
        border-title-align: center;
        border-title-color: $accent;
        border-title-background: $surface;
        overflow: auto;
    }
    
    #deployment-details {
        width: 50%;
        height: 100%;
        padding: 0;
        border: solid $accent;
        border-title-align: center;
        border-title-color: $accent;
        border-title-background: $surface;
        overflow: auto;
    }
    
    #clusters-list {
        width: 50%;
        height: 100%;
        padding: 0;
        border: solid $accent;
        border-title-align: center;
        border-title-color: $accent;
        border-title-background: $surface;
        overflow: auto;
    }
    
    #cluster-details {
        width: 50%;
        height: 100%;
        padding: 0;
        border: solid $accent;
        border-title-align: center;
        border-title-color: $accent;
        border-title-background: $surface;
        overflow: auto;
    }
    
    #apps-list {
        width: 50%;
        height: 100%;
        padding: 0;
        border: solid $accent;
        border-title-align: center;
        border-title-color: $accent;
        border-title-background: $surface;
        overflow: auto;
    }
    
    #app-details {
        width: 50%;
        height: 100%;
        padding: 0;
        border: solid $accent;
        border-title-align: center;
        border-title-color: $accent;
        border-title-background: $surface;
        overflow: auto;
    }
    
    /* DataTables fill their containers */
    #deployments-table, #clusters-table, #apps-table,
    #deployment-details-table, #cluster-details-table, #app-details-table {
        height: 100%;
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
        clusters: Optional[List[Cluster]] = None,
        deployments: Optional[List[Deployment]] = None,
        apps: Optional[List[Any]] = None,
    ):
        super().__init__()

        # Configuration
        self.config = config or DashboardConfig()
        self.services = services or self._get_default_services()
        self.custom_handlers = custom_handlers or {}
        self.platform_info = platform_info or self._get_default_platform_info()
        self.ctx = ctx 
        # SDK data
        self.clusters = clusters or []
        self.deployments = deployments or []
        self.apps = apps or []
        self.credentials = []  # Will be loaded from SDK
        
        # Selected items for details display
        self.selected_deployment = None
        self.selected_cluster = None
        self.selected_app = None

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

    @classmethod
    def from_sdk_data(
        cls,
        clusters: Optional[List[Cluster]] = None,
        deployments: Optional[List[Deployment]] = None,
        apps: Optional[List[Any]] = None,
        config: Optional[DashboardConfig] = None,
        custom_handlers: Optional[Dict[str, Callable[..., Any]]] = None,
        platform_info: Optional[Dict[str, str]] = None,
        ctx: Optional[typer.Context] = None,
    ) -> "DashboardApp":
        """Create a DashboardApp from SDK cluster and deployment objects.
        
        This is a convenience method that converts SDK schemas into ServiceConfig
        objects and initializes the dashboard.
        
        Args:
            clusters: List of Cluster objects from cluster SDK
            deployments: List of Deployment objects from deployment SDK
            config: Dashboard configuration
            custom_handlers: Optional custom worker handlers
            platform_info: Platform information to display
            ctx: Typer context with SDK configuration
            
        Returns:
            Configured DashboardApp instance
            
        Example:
            ```python
            from vantage_cli.sdk.cluster import cluster_sdk
            from vantage_cli.sdk.deployment import deployment_sdk
            
            clusters = await cluster_sdk.list_clusters(ctx)
            deployments = await deployment_sdk.list(ctx)
            
            app = DashboardApp.from_sdk_data(
                clusters=clusters,
                deployments=deployments,
                ctx=ctx
            )
            app.run()
            ```
        """
        services = []
        
        if clusters:
            services.extend([ServiceConfig.from_cluster(c) for c in clusters])
            
        if deployments:
            services.extend([ServiceConfig.from_deployment(d) for d in deployments])
        
        return cls(
            config=config,
            services=services,
            custom_handlers=custom_handlers,
            platform_info=platform_info,
            ctx=ctx,
            clusters=clusters,
            deployments=deployments,
            apps=apps,
        )

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
            handler = self.custom_handlers.get(service.name, lambda x: {"duration": 1.0})
            worker = Worker(service.name, handler, WorkerState.INIT, service.dependencies)
            workers.append(worker)
        return workers

    def compose(self) -> ComposeResult:
        """Create the dashboard layout"""
        import logging
        logger = logging.getLogger(__name__)
        print(f"DEBUG: compose() called - clusters: {len(self.clusters)}, deployments: {len(self.deployments)}, apps: {len(self.apps)}")
        logger.debug(f"compose() called - clusters: {len(self.clusters)}, deployments: {len(self.deployments)}, apps: {len(self.apps)}")
        
        yield CustomHeader()

        with Horizontal(id="tab-and-buttons-container"):
            with TabbedContent(initial="main", id="main-content"):
                with TabPane("📊 Dashboard", id="main"):
                    with Vertical():
                        with Horizontal(id="main-panel"):
                            # Left side: Three stacked horizontal panels with tables
                            with Vertical(id="left-content"):
                                # Panel 1: Deployments (table + details)
                                with Horizontal(id="deployments-panel"):
                                    with Vertical(id="deployments-list"):
                                        yield DataTable(id="main-deployments-table", zebra_stripes=True)
                                    with Vertical(id="deployment-details"):
                                        yield DataTable(id="main-deployment-details-table")
                                
                                # Panel 2: Clusters (table + details)
                                with Horizontal(id="clusters-panel"):
                                    with Vertical(id="clusters-list"):
                                        yield DataTable(id="main-clusters-table", zebra_stripes=True)
                                    with Vertical(id="cluster-details"):
                                        yield DataTable(id="main-cluster-details-table")
                                
                                # Panel 3: Apps (table + details)
                                with Horizontal(id="apps-panel"):
                                    with Vertical(id="apps-list"):
                                        yield DataTable(id="apps-table", zebra_stripes=True)
                                    with Vertical(id="app-details"):
                                        yield DataTable(id="app-details-table")

                            # Right side: Activity log and platform info (unchanged)
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

                # Add credentials management tab if context is available
                if self.ctx:
                    yield CredentialManagementTabPane(
                        title="Credentials",
                        ctx=self.ctx,
                        credentials=self.credentials if hasattr(self, 'credentials') else [],
                        id="credentials-tab"
                    )

                # Add deployment management tab if context is available
                if self.ctx:
                    yield DeploymentManagementTabPane(self.ctx)

            # Control buttons
            if self.config.enable_controls:
                with Vertical(id="control-buttons"):
                    yield Button("Create", id="start-btn", variant="success", classes="tab-button")
                    yield Button("Status", id="stop-btn", variant="error", classes="tab-button")
                    yield Button(
                        "Remove", id="restart-btn", variant="primary", classes="tab-button"
                    )
                    yield Button(
                        "Logout", id="auth-btn", variant="warning", classes="tab-button"
                    )

        # Footer
        yield Static(
            f"🚀 {self.platform_info['name']} - {self.config.title} | Press Ctrl+C to quit",
            id="footer",
        )

    def on_ready(self) -> None:
        """Initialize the dashboard when app is ready"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.debug(f"on_ready called - clusters: {len(self.clusters)}, deployments: {len(self.deployments)}, apps: {len(self.apps)}")
        
        self.add_log(f"🎯 {self.config.title} initialized")
        self.add_log("💡 Use Ctrl+C or 'q' to quit, 'r' to restart")

        # Defer table setup to allow widgets to mount
        self.call_later(self.setup_tables)

        if self.config.enable_stats:
            self.set_interval(self.config.refresh_interval, self.refresh_stats)
        
        # Load and refresh the debug log file
        if self.config.enable_logs:
            self.call_later(self.load_debug_log)
            self.set_interval(2.0, self.refresh_debug_log)  # Refresh every 2 seconds
    
    def on_mount(self) -> None:
        """Called when the app is mounted"""
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"on_mount called - clusters: {len(self.clusters)}, deployments: {len(self.deployments)}, apps: {len(self.apps)}")
        
        # Load credentials from SDK
        self.load_credentials()
        
        # Update auth button based on login status
        self.call_later(self._update_auth_button)
        
        # Try setup_tables here too
        self.call_later(self.setup_tables)
    
    def load_credentials(self) -> None:
        """Load credentials from the SDK."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            from vantage_cli.sdk.cloud_credential.crud import cloud_credential_sdk
            self.credentials = cloud_credential_sdk.list()
            logger.debug(f"Loaded {len(self.credentials)} credentials from SDK")
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            self.credentials = []

    def setup_tables(self):
        """Set up the data tables"""
        import logging
        logger = logging.getLogger(__name__)
        logger.debug("setup_tables called")
        
        try:
            # Set border titles for containers
            self.query_one("#deployments-list").border_title = "📦 Deployments"
            self.query_one("#deployment-details").border_title = "📋 Deployment Details"
            self.query_one("#clusters-list").border_title = "🖥️  Clusters"
            self.query_one("#cluster-details").border_title = "📋 Cluster Details"
            self.query_one("#apps-list").border_title = "📱 Apps"
            self.query_one("#app-details").border_title = "📋 App Details"
            
            # Initialize Deployments table
            deployments_table = self.query_one("#main-deployments-table", DataTable)
            deployments_table.add_columns("Name", "App", "Cluster", "Status")
            deployments_table.cursor_type = "row"
            
            # Initialize Deployment Details table
            deployment_details_table = self.query_one("#main-deployment-details-table", DataTable)
            deployment_details_table.add_columns("Property", "Value")
            deployment_details_table.show_header = False
            
            # Initialize Clusters table
            clusters_table = self.query_one("#main-clusters-table", DataTable)
            clusters_table.add_columns("Name", "Status", "Type", "Region")
            clusters_table.cursor_type = "row"
            
            # Initialize Cluster Details table
            cluster_details_table = self.query_one("#main-cluster-details-table", DataTable)
            cluster_details_table.add_columns("Property", "Value")
            cluster_details_table.show_header = False
            
            # Initialize Apps table
            apps_table = self.query_one("#apps-table", DataTable)
            apps_table.add_columns("Name", "Cloud", "Substrate", "Status")
            apps_table.cursor_type = "row"
            
            # Initialize App Details table
            app_details_table = self.query_one("#app-details-table", DataTable)
            app_details_table.add_columns("Property", "Value")
            app_details_table.show_header = False
            
            # Populate tables with data
            self.populate_deployments_table()
            self.populate_clusters_table()
            self.populate_apps_table()
            
            logger.debug("setup_tables completed successfully")
        except Exception as e:
            logger.exception(f"Error in setup_tables: {e}")

    def populate_deployments_table(self):
        """Populate the deployments table with data"""
        import logging
        logger = logging.getLogger(__name__)
        
        deployments_table = self.query_one("#main-deployments-table", DataTable)
        deployments_table.clear()
        
        logger.debug(f"Populating deployments table with {len(self.deployments)} deployments")
        
        if not self.deployments:
            # Add a placeholder row if no deployments
            deployments_table.add_row("(No deployments found)", "", "", "", key="empty")
            return
        
        for deployment in self.deployments:
            # Use deployment name or construct one
            name = deployment.name if hasattr(deployment, 'name') else f"{deployment.app_name}-{deployment.cluster.name if deployment.cluster else 'unknown'}"
            app_name = deployment.app_name if hasattr(deployment, 'app_name') else "N/A"
            cluster_name = deployment.cluster.name if deployment.cluster else "N/A"
            status = deployment.status or "Unknown"
            deployment_id = deployment.id if hasattr(deployment, 'id') else name
            
            deployments_table.add_row(
                name,
                app_name,
                cluster_name,
                status,
                key=str(deployment_id)
            )
    
    def populate_clusters_table(self):
        """Populate the clusters table with data"""
        import logging
        logger = logging.getLogger(__name__)
        
        clusters_table = self.query_one("#main-clusters-table", DataTable)
        clusters_table.clear()
        
        logger.debug(f"Populating clusters table with {len(self.clusters)} clusters")
        
        if not self.clusters:
            # Add a placeholder row if no clusters
            clusters_table.add_row("(No clusters found)", "", "", "", key="empty")
            return
        
        for cluster in self.clusters:
            status = cluster.status or "Unknown"
            cluster_type = cluster.cluster_type if hasattr(cluster, 'cluster_type') else cluster.provider
            region = cluster.creation_parameters.get('region', 'N/A') if cluster.creation_parameters else "N/A"
            
            logger.debug(f"Adding cluster row: name={cluster.name}, status={status}, type={cluster_type}, region={region}")
            
            clusters_table.add_row(
                cluster.name,
                status,
                cluster_type,
                region,
                key=cluster.name
            )
        
        # Verify table was populated
        logger.debug(f"Clusters table now has {clusters_table.row_count} rows")
        logger.debug(f"Clusters table visible: {clusters_table.visible}, display: {clusters_table.display}")
    
    def populate_apps_table(self):
        """Populate the apps table with data"""
        import logging
        logger = logging.getLogger(__name__)
        
        apps_table = self.query_one("#apps-table", DataTable)
        apps_table.clear()
        
        logger.debug(f"Populating apps table with {len(self.apps)} apps")
        
        if not self.apps:
            # Add a placeholder row if no apps
            apps_table.add_row("(No apps found)", "", "", "", key="empty")
            return
        
        for app in self.apps:
            cloud = getattr(app, 'cloud', 'N/A')
            substrate = getattr(app, 'substrate', 'N/A')
            status = getattr(app, 'status', 'Unknown')
            name = getattr(app, 'name', 'Unknown')
            
            apps_table.add_row(
                name,
                cloud,
                substrate,
                status,
                key=name
            )
    
    def update_deployment_details(self, deployment):
        """Update deployment details table with selected deployment info"""
        details_table = self.query_one("#main-deployment-details-table", DataTable)
        details_table.clear()
        
        if deployment is None:
            return
        
        # Add deployment details
        details_table.add_row("App Name", deployment.app_name)
        details_table.add_row("ID", str(deployment.id) if hasattr(deployment, 'id') else "N/A")
        details_table.add_row("Status", deployment.status or "Unknown")
        details_table.add_row("Substrate", deployment.substrate or "N/A")
        
        if deployment.cluster:
            details_table.add_row("Cluster", deployment.cluster.name)
            details_table.add_row("Cluster Status", deployment.cluster.status)
        
        if hasattr(deployment, 'cloud'):
            details_table.add_row("Cloud", str(deployment.cloud))
        
        if hasattr(deployment, 'created_at') and deployment.created_at:
            details_table.add_row("Created", str(deployment.created_at))
        
        if hasattr(deployment, 'updated_at') and deployment.updated_at:
            details_table.add_row("Updated", str(deployment.updated_at))
    
    def update_cluster_details(self, cluster):
        """Update cluster details table with selected cluster info"""
        details_table = self.query_one("#main-cluster-details-table", DataTable)
        details_table.clear()
        
        if cluster is None:
            return
        
        # Add cluster details
        details_table.add_row("Name", cluster.name)
        details_table.add_row("Status", cluster.status or "Unknown")
        details_table.add_row("Provider", cluster.provider or "N/A")
        details_table.add_row("Type", cluster.cluster_type if hasattr(cluster, 'cluster_type') else cluster.provider)
        
        if cluster.description:
            details_table.add_row("Description", cluster.description)
        
        if cluster.owner_email:
            details_table.add_row("Owner", cluster.owner_email)
        
        if cluster.creation_parameters:
            region = cluster.creation_parameters.get('region', 'N/A')
            details_table.add_row("Region", region)
            
            machine_type = cluster.creation_parameters.get('machine_type', 'N/A')
            if machine_type != 'N/A':
                details_table.add_row("Machine Type", machine_type)
            
            node_count = cluster.creation_parameters.get('node_count', 'N/A')
            if node_count != 'N/A':
                details_table.add_row("Nodes", str(node_count))
    
    def update_app_details(self, app):
        """Update app details table with selected app info"""
        details_table = self.query_one("#app-details-table", DataTable)
        details_table.clear()
        
        if app is None:
            return
        
        # Add app details
        name = getattr(app, 'name', 'Unknown')
        details_table.add_row("Name", name)
        
        if hasattr(app, 'id'):
            details_table.add_row("ID", str(app.id))
        
        if hasattr(app, 'cloud'):
            details_table.add_row("Cloud", str(app.cloud))
        
        if hasattr(app, 'substrate'):
            details_table.add_row("Substrate", str(app.substrate))
        
        if hasattr(app, 'status'):
            details_table.add_row("Status", str(app.status))
        
        if hasattr(app, 'created_at') and app.created_at:
            details_table.add_row("Created", str(app.created_at))
        
        if hasattr(app, 'description') and app.description:
            details_table.add_row("Description", str(app.description))
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in any of the tables"""
        table_id = event.data_table.id
        
        if table_id == "main-deployments-table":
            # Find the selected deployment by ID
            row_key = event.row_key
            for deployment in self.deployments:
                deployment_id = deployment.id if hasattr(deployment, 'id') else deployment.app_name
                if deployment_id == row_key:
                    self.selected_deployment = deployment
                    self.update_deployment_details(deployment)
                    break
        
        elif table_id == "main-clusters-table":
            # Find the selected cluster by name
            row_key = event.row_key
            for cluster in self.clusters:
                if cluster.name == row_key:
                    self.selected_cluster = cluster
                    self.update_cluster_details(cluster)
                    break
        
        elif table_id == "apps-table":
            # Find the selected app by name
            row_key = event.row_key
            for app in self.apps:
                app_name = getattr(app, 'name', None)
                if app_name == row_key:
                    self.selected_app = app
                    self.update_app_details(app)
                    break

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
    
    def load_debug_log(self):
        """Load the debug log file into the full logs widget"""
        from pathlib import Path
        
        try:
            log_file = Path.home() / ".vantage-cli" / "debug.log"
            if not log_file.exists():
                return
            
            full_log = self.query_one("#full-logs", RichLog)
            full_log.clear()
            
            # Read last 500 lines to avoid overwhelming the widget
            with open(log_file, 'r') as f:
                lines = f.readlines()
                # Get last 500 lines
                recent_lines = lines[-500:] if len(lines) > 500 else lines
                
                for line in recent_lines:
                    # Remove trailing newline and write to log
                    full_log.write(line.rstrip())
            
            # Track the file position for incremental updates
            self._log_file_position = log_file.stat().st_size
            
        except Exception as e:
            # Silently handle errors - don't want to crash dashboard
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Error loading debug log: {e}")
    
    def refresh_debug_log(self):
        """Refresh the debug log with new entries"""
        from pathlib import Path
        
        try:
            log_file = Path.home() / ".vantage-cli" / "debug.log"
            if not log_file.exists():
                return
            
            # Initialize position tracker if not exists
            if not hasattr(self, '_log_file_position'):
                self._log_file_position = 0
            
            current_size = log_file.stat().st_size
            
            # Only read if file has grown
            if current_size > self._log_file_position:
                full_log = self.query_one("#full-logs", RichLog)
                
                with open(log_file, 'r') as f:
                    # Seek to last known position
                    f.seek(self._log_file_position)
                    # Read new lines
                    new_lines = f.readlines()
                    
                    for line in new_lines:
                        full_log.write(line.rstrip())
                
                # Update position tracker
                self._log_file_position = current_size
            
        except Exception as e:
            # Silently handle errors
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Error refreshing debug log: {e}")

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
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "start-btn":
            # Context-aware Create button based on active tab
            self.handle_create_action()
        elif event.button.id == "stop-btn":
            self.action_stop_execution()
        elif event.button.id == "restart-btn":
            # Context-aware Remove button based on active tab
            self.handle_remove_action()
        elif event.button.id == "auth-btn":
            # Handle Login/Logout button
            self.handle_auth_action()
        elif event.button.id == "clear-all-btn":
            self.action_clear_logs()
        elif event.button.id == "export-btn":
            self.action_export_logs()
    
    def handle_create_action(self):
        """Handle Create button based on active tab"""
        try:
            # Get the active tab
            tabbed_content = self.query_one(TabbedContent)
            active_tab = tabbed_content.active
            
            if active_tab == "clusters-tab":
                # Open cluster creation modal
                self.open_create_cluster_modal()
            elif active_tab == "credentials-tab":
                # Open credential creation modal
                self.open_create_credential_modal()
            elif active_tab == "deployments-tab":
                # Future: Open deployment creation modal
                self.add_log("📦 Deployment creation coming soon", "INFO")
            elif active_tab == "profiles-tab":
                # Open profile creation modal
                self.open_create_profile_modal()
            else:
                # Default: start worker execution
                self.action_start_execution()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Error handling create action: {e}")
            # Fallback to default action
            self.action_start_execution()
    
    def open_create_cluster_modal(self):
        """Open the cluster creation modal"""
        def handle_cluster_creation(cluster_data: Optional[Dict[str, str]]) -> None:
            """Handle the result from cluster creation modal"""
            if cluster_data:
                self.add_log(
                    f"🖥️  Creating cluster: {cluster_data['name']} on {cluster_data['cloud']}", 
                    "INFO"
                )
                # Create the cluster via SDK (triggers async work)
                self.create_cluster_from_modal(cluster_data)
            else:
                self.add_log("❌ Cluster creation cancelled", "INFO")
        
        # Push the modal screen and handle the result
        self.push_screen(CreateClusterModal(), handle_cluster_creation)
    
    @work(exclusive=True)
    async def create_cluster_from_modal(self, cluster_data: Dict[str, str]) -> None:
        """Create a cluster using the SDK.
        
        Args:
            cluster_data: Dictionary with name, description, and cloud provider
        """
        from vantage_cli.sdk.cluster.crud import cluster_sdk
        
        if not self.ctx:
            self.add_log("❌ No context available for cluster creation", "ERROR")
            self.notify("Cannot create cluster: no context available", severity="error")
            return
        
        try:
            # Show creating status
            self.notify("Creating cluster...", severity="information")
            
            # Normalize provider name (convert display name to API format)
            provider_map = {
                "aws": "aws",
                "gcp": "gcp", 
                "azure": "azure",
                "cudo-compute": "cudo-compute",
                "on-premises": "on_prem",
                "k8s": "k8s",
                "localhost": "localhost",
            }
            
            provider = provider_map.get(cluster_data['cloud'].lower(), cluster_data['cloud'])
            
            # Create the cluster
            new_cluster = await cluster_sdk.create_cluster(
                ctx=self.ctx,
                name=cluster_data['name'],
                provider=provider,
                description=cluster_data['description'] if cluster_data['description'] else None,
            )
            
            self.add_log(
                f"✅ Successfully created cluster: {new_cluster.name} (ID: {new_cluster.client_id})",
                "SUCCESS"
            )
            
            self.notify(
                f"Cluster '{new_cluster.name}' created successfully!",
                severity="information",
                timeout=5
            )
            
            # Add to local clusters list
            self.clusters.append(new_cluster)
            
            # Refresh the clusters table if we're on the main dashboard
            try:
                self.populate_clusters_table()
            except Exception:
                pass
            
            # Notify the ClusterManagementTabPane to refresh if it exists
            try:
                cluster_tab = self.query_one(ClusterManagementTabPane)
                cluster_tab.refresh_clusters()
            except Exception:
                pass
                
        except Exception as e:
            error_msg = f"Failed to create cluster: {str(e)}"
            self.add_log(f"❌ {error_msg}", "ERROR")
            self.notify(error_msg, severity="error", timeout=10)
            
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Cluster creation failed")

    def open_create_credential_modal(self):
        """Open the credential creation modal"""
        def handle_credential_creation(credential_data: Optional[dict]) -> None:
            """Handle the result from credential creation modal"""
            if credential_data:
                self.add_log(
                    f"🔐 Creating credential: {credential_data['name']} ({credential_data['credential_type']})", 
                    "INFO"
                )
                # Create the credential via SDK (triggers async work)
                self.create_credential_from_modal(credential_data)
            else:
                self.add_log("❌ Credential creation cancelled", "INFO")
        
        # Push the modal screen and handle the result
        self.push_screen(CreateCredentialModal(), handle_credential_creation)
    
    @work(exclusive=True)
    async def create_credential_from_modal(self, credential_data: dict) -> None:
        """Create a credential using the SDK.
        
        Args:
            credential_data: Dictionary with credential information
        """
        from vantage_cli.sdk.cloud_credential.crud import cloud_credential_sdk
        from vantage_cli.sdk.cloud.schema import CloudType
        
        try:
            # Show creating status
            self.notify("Creating credential...", severity="information")
            
            # Convert credential type string to CloudType enum
            try:
                cred_type = CloudType(credential_data['credential_type'])
            except ValueError:
                cred_type = CloudType.CUDO_COMPUTE  # Default fallback
            
            # Create the credential
            new_credential = cloud_credential_sdk.create(
                name=credential_data['name'],
                credential_type=cred_type,
                cloud_id=credential_data['cloud_id'],
                credentials_data=credential_data['credentials_data'],
            )
            
            # Set as default if requested
            if credential_data.get('default', False):
                cloud_credential_sdk.update(
                    credential_id=new_credential.id,
                    set_as_default=True
                )
            
            self.add_log(
                f"✅ Successfully created credential: {new_credential.name} (ID: {new_credential.id})",
                "SUCCESS"
            )
            
            self.notify(
                f"Credential '{new_credential.name}' created successfully!",
                severity="information",
                timeout=5
            )
            
            # Add to local credentials list
            self.credentials.append(new_credential)
            
            # Notify the CredentialManagementTabPane to refresh if it exists
            try:
                credential_tab = self.query_one(CredentialManagementTabPane)
                credential_tab.refresh_credentials()
            except Exception:
                pass
                
        except Exception as e:
            error_msg = f"Failed to create credential: {str(e)}"
            self.add_log(f"❌ {error_msg}", "ERROR")
            self.notify(error_msg, severity="error", timeout=10)
            
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Credential creation failed")

    def open_remove_credential_modal(self):
        """Open the credential removal modal"""
        if not self.credentials:
            self.add_log("❌ No credentials available to remove", "WARNING")
            self.notify("No credentials available to remove", severity="warning")
            return
        
        def handle_credential_removal(credential_id: Optional[str]) -> None:
            """Handle the result from credential removal modal"""
            if credential_id:
                # Find the credential name
                credential = next((c for c in self.credentials if c.id == credential_id), None)
                if credential:
                    self.add_log(
                        f"🗑️  Removing credential: {credential.name}", 
                        "INFO"
                    )
                    # Remove the credential via SDK (triggers async work)
                    self.remove_credential_from_modal(credential_id)
            else:
                self.add_log("❌ Credential removal cancelled", "INFO")
        
        # Push the modal screen and handle the result
        self.push_screen(RemoveCredentialModal(self.credentials), handle_credential_removal)
    
    @work(exclusive=True)
    async def remove_credential_from_modal(self, credential_id: str) -> None:
        """Remove a credential using the SDK.
        
        Args:
            credential_id: ID of the credential to remove
        """
        from vantage_cli.sdk.cloud_credential.crud import cloud_credential_sdk
        
        try:
            # Show removing status
            self.notify("Removing credential...", severity="information")
            
            # Find the credential object
            credential = next((c for c in self.credentials if c.id == credential_id), None)
            if not credential:
                self.add_log(f"❌ Credential '{credential_id}' not found", "ERROR")
                self.notify(f"Credential '{credential_id}' not found", severity="error")
                return
            
            # Remove the credential
            success = cloud_credential_sdk.delete(credential_id)
            
            if success:
                self.add_log(
                    f"✅ Successfully removed credential: {credential.name}",
                    "SUCCESS"
                )
                
                self.notify(
                    f"Credential '{credential.name}' removed successfully!",
                    severity="information",
                    timeout=5
                )
                
                # Remove from local credentials list
                self.credentials = [c for c in self.credentials if c.id != credential_id]
                
                # Notify the CredentialManagementTabPane to refresh if it exists
                try:
                    credential_tab = self.query_one(CredentialManagementTabPane)
                    credential_tab.refresh_credentials()
                except Exception:
                    pass
            else:
                raise Exception("Credential deletion returned False")
                
        except Exception as e:
            error_msg = f"Failed to remove credential: {str(e)}"
            self.add_log(f"❌ {error_msg}", "ERROR")
            self.notify(error_msg, severity="error", timeout=10)
            
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Credential removal failed")

    def open_create_profile_modal(self):
        """Open the profile creation modal"""
        def handle_profile_creation(profile_data: Optional[dict]) -> None:
            """Handle the result from profile creation modal"""
            if profile_data:
                self.add_log(
                    f"👤 Creating profile: {profile_data['name']}", 
                    "INFO"
                )
                # Create the profile via SDK (triggers async work)
                self.create_profile_from_modal(profile_data)
            else:
                self.add_log("❌ Profile creation cancelled", "INFO")
        
        # Push the modal screen and handle the result
        self.push_screen(CreateProfileModal(), handle_profile_creation)
    
    @work(exclusive=True)
    async def create_profile_from_modal(self, profile_data: dict) -> None:
        """Create a profile using the SDK.
        
        Args:
            profile_data: Dictionary with profile information
        """
        try:
            # Show creating status
            self.notify("Creating profile...", severity="information")
            
            # Extract activation flag
            activate = profile_data.pop("activate", False)
            
            # Create the profile
            new_profile = await profile_sdk.create(
                ctx=self.ctx,
                resource_data=profile_data,
                activate=activate
            )
            
            self.add_log(
                f"✅ Successfully created profile: {new_profile['name']}",
                "SUCCESS"
            )
            
            self.notify(
                f"Profile '{new_profile['name']}' created successfully!",
                severity="information",
                timeout=5
            )
            
            # Notify the ProfileManagementTabPane to refresh if it exists
            try:
                profile_tab = self.query_one(ProfileManagementTabPane)
                profile_tab.refresh_profiles()
            except Exception:
                pass
                
        except Exception as e:
            error_msg = f"Failed to create profile: {str(e)}"
            self.add_log(f"❌ {error_msg}", "ERROR")
            self.notify(error_msg, severity="error", timeout=10)
            
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Profile creation failed")

    def open_remove_profile_modal(self):
        """Open the profile removal modal"""
        # Get current profiles from the profile tab
        try:
            profile_tab = self.query_one(ProfileManagementTabPane)
            profiles = profile_tab.profiles
        except Exception:
            profiles = []
        
        if not profiles:
            self.add_log("❌ No profiles available to remove", "WARNING")
            self.notify("No profiles available to remove", severity="warning")
            return
        
        def handle_profile_removal(profile_name: Optional[str]) -> None:
            """Handle the result from profile removal modal"""
            if profile_name:
                self.add_log(
                    f"🗑️  Removing profile: {profile_name}", 
                    "INFO"
                )
                # Remove the profile via SDK (triggers async work)
                self.remove_profile_from_modal(profile_name)
            else:
                self.add_log("❌ Profile removal cancelled", "INFO")
        
        # Push the modal screen and handle the result
        self.push_screen(RemoveProfileModal(profiles), handle_profile_removal)
    
    @work(exclusive=True)
    async def remove_profile_from_modal(self, profile_name: str) -> None:
        """Remove a profile using the SDK.
        
        Args:
            profile_name: Name of the profile to remove
        """
        try:
            # Show removing status
            self.notify("Removing profile...", severity="information")
            
            # Check if trying to remove 'default' profile
            force = False
            if profile_name == "default":
                self.add_log(
                    "⚠️  Attempting to remove 'default' profile (force=True)",
                    "WARNING"
                )
                force = True
            
            # Remove the profile
            success = await profile_sdk.delete(
                ctx=self.ctx,
                resource_id=profile_name,
                force=force
            )
            
            if success:
                self.add_log(
                    f"✅ Successfully removed profile: {profile_name}",
                    "SUCCESS"
                )
                
                self.notify(
                    f"Profile '{profile_name}' removed successfully!",
                    severity="information",
                    timeout=5
                )
                
                # Notify the ProfileManagementTabPane to refresh if it exists
                try:
                    profile_tab = self.query_one(ProfileManagementTabPane)
                    profile_tab.refresh_profiles()
                except Exception:
                    pass
            else:
                raise Exception("Profile deletion returned False")
                
        except Exception as e:
            error_msg = f"Failed to remove profile: {str(e)}"
            self.add_log(f"❌ {error_msg}", "ERROR")
            self.notify(error_msg, severity="error", timeout=10)
            
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Profile removal failed")

    def handle_remove_action(self):
        """Handle Remove button based on active tab"""
        try:
            # Get the active tab
            tabbed_content = self.query_one(TabbedContent)
            active_tab = tabbed_content.active
            
            if active_tab == "clusters-tab":
                # Open cluster removal modal
                self.open_remove_cluster_modal()
            elif active_tab == "credentials-tab":
                # Open credential removal modal
                self.open_remove_credential_modal()
            elif active_tab == "deployments-tab":
                # Future: Open deployment removal modal
                self.add_log("📦 Deployment removal coming soon", "INFO")
            elif active_tab == "profiles-tab":
                # Open profile removal modal
                self.open_remove_profile_modal()
            else:
                # Default: restart execution (old behavior)
                self.action_restart()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Error handling remove action: {e}")
            # Fallback to default action
            self.action_restart()
    
    def handle_auth_action(self):
        """Handle Login/Logout button"""
        # Check if user is logged in
        if self._is_logged_in():
            # User is logged in, perform logout
            self.perform_logout()
        else:
            # User is not logged in, show login modal
            self.open_login_modal()
    
    def _is_logged_in(self) -> bool:
        """Check if user is currently logged in with a valid token.
        
        Returns:
            True if valid token exists, False otherwise
        """
        if not self.ctx:
            return False
            
        try:
            # Try to load tokens from cache
            token_set = load_tokens_from_cache(self.ctx.obj.profile)
            
            # Check if access token is valid (not expired)
            if token_set.access_token and not is_token_expired(token_set.access_token):
                return True
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Error checking login status: {e}")
        
        return False
    
    def _get_logged_in_email(self) -> Optional[str]:
        """Get the email of the currently logged in user.
        
        Returns:
            Email if logged in, None otherwise
        """
        if not self.ctx:
            return None
            
        try:
            token_set = load_tokens_from_cache(self.ctx.obj.profile)
            if token_set.access_token and not is_token_expired(token_set.access_token):
                persona = extract_persona(self.ctx.obj.profile, token_set)
                return persona.identity_data.email
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Error getting logged in email: {e}")
        
        return None
    
    def _update_auth_button(self):
        """Update the auth button text based on login status"""
        try:
            auth_btn = self.query_one("#auth-btn", Button)
            if self._is_logged_in():
                auth_btn.label = "Logout"
                auth_btn.variant = "warning"
            else:
                auth_btn.label = "Login"
                auth_btn.variant = "success"
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Error updating auth button: {e}")
    
    def open_login_modal(self):
        """Open the login modal and start authentication"""
        def handle_login_result(success: Optional[bool]) -> None:
            """Handle the result from login modal"""
            if success:
                self.add_log("✅ Login successful", "SUCCESS")
                self._update_auth_button()
            elif success is False:
                self.add_log("❌ Login cancelled", "INFO")
        
        # Create and show the modal
        login_modal = LoginModal()
        self.push_screen(login_modal, handle_login_result)
        
        # Start the login process
        self.perform_login(login_modal)
    
    @work(exclusive=True)
    async def perform_login(self, modal: LoginModal) -> None:
        """Perform login authentication with modal updates
        
        Args:
            modal: The LoginModal instance to update with progress
        """
        if not self.ctx:
            modal.set_status("No context available for login", is_error=True)
            self.add_log("❌ No context available for login", "ERROR")
            return
        
        try:
            # Check if ctx is a CliContext or has the profile attribute
            if not hasattr(self.ctx.obj, 'profile'):
                error_msg = "Context does not have profile information. Cannot authenticate."
                modal.set_status(error_msg, is_error=True)
                self.add_log(f"❌ {error_msg}", "ERROR")
                return
            
            # Check if already logged in
            existing_email = self._get_logged_in_email()
            if existing_email:
                modal.set_status(f"Already authenticated as {existing_email}", is_complete=True)
                self.add_log(f"✅ Already logged in as: {existing_email}", "INFO")
                return
            
            modal.set_status("Initializing authentication...")
            
            # Ensure settings are loaded
            if not hasattr(self.ctx.obj, 'settings') or self.ctx.obj.settings is None:
                import json
                from vantage_cli.constants import USER_CONFIG_FILE
                from vantage_cli.config import init_settings
                
                try:
                    modal.set_status("Loading settings...")
                    settings_all_profiles = json.loads(USER_CONFIG_FILE.read_text())
                    settings_values = settings_all_profiles.get(self.ctx.obj.profile)
                    if not settings_values:
                        error_msg = f"No settings found for profile '{self.ctx.obj.profile}'. Run 'vantage config set' first."
                        modal.set_status(error_msg, is_error=True)
                        raise Exception(error_msg)
                    self.ctx.obj.settings = init_settings(**settings_values)
                except FileNotFoundError:
                    error_msg = (
                        f"No settings file found. "
                        "Run 'vantage config set' first to establish your OIDC settings."
                    )
                    modal.set_status(error_msg, is_error=True)
                    raise Exception(error_msg)
            
            modal.set_status("Setting up authentication client...")
            
            # Create HTTP client and perform authentication
            import httpx
            import datetime
            from vantage_cli.constants import OIDC_DEVICE_PATH, OIDC_TOKEN_PATH
            from vantage_cli.schemas import DeviceCodeData, TokenSet
            from vantage_cli.client import make_oauth_request
            
            async with httpx.AsyncClient(
                base_url=self.ctx.obj.settings.get_auth_url(),
                headers={"content-type": "application/x-www-form-urlencoded"},
            ) as client:
                self.ctx.obj.client = client
                
                # Get device code
                modal.set_status("Requesting authentication code...")
                device_code_data: DeviceCodeData = await make_oauth_request(
                    client,
                    OIDC_DEVICE_PATH,
                    data={"client_id": self.ctx.obj.settings.oidc_client_id},
                    response_model_cls=DeviceCodeData,
                    abort_message="Could not retrieve device verification code",
                    abort_subject="COULD NOT RETRIEVE TOKEN",
                )
                
                # Show URL to user
                auth_url = device_code_data.verification_uri_complete
                modal.set_status(
                    "Waiting for browser authentication...",
                    show_url=True,
                    url=auth_url
                )
                self.add_log(f"🔗 Authentication URL: {auth_url}", "INFO")
                
                # Poll for token
                start_time = datetime.datetime.now()
                timeout_seconds = self.ctx.obj.settings.oidc_max_poll_time
                interval = device_code_data.interval
                
                while True:
                    elapsed = (datetime.datetime.now() - start_time).total_seconds()
                    
                    # Check timeout
                    if elapsed >= timeout_seconds:
                        modal.set_status("Authentication timed out", is_error=True)
                        raise Exception("Authentication timed out")
                    
                    # Wait for interval
                    await asyncio.sleep(interval)
                    
                    # Try to get token
                    try:
                        response = await client.post(
                            OIDC_TOKEN_PATH,
                            data={
                                "client_id": self.ctx.obj.settings.oidc_client_id,
                                "device_code": device_code_data.device_code,
                                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                            },
                        )
                        
                        if response.status_code == 200:
                            # Success! Got the token
                            token_data = response.json()
                            token_set = TokenSet(
                                access_token=token_data.get("access_token", ""),
                                refresh_token=token_data.get("refresh_token"),
                            )
                            
                            # Extract persona and save
                            from vantage_cli.cache import save_tokens_to_cache
                            save_tokens_to_cache(self.ctx.obj.profile, token_set)
                            persona = extract_persona(self.ctx.obj.profile, token_set)
                            
                            # Update modal to success
                            modal.set_status(
                                f"Successfully authenticated as {persona.identity_data.email}",
                                is_complete=True
                            )
                            self.add_log(
                                f"✅ Successfully authenticated as: {persona.identity_data.email}",
                                "SUCCESS"
                            )
                            
                            # Update the button
                            self._update_auth_button()
                            break
                        
                        elif response.status_code == 400:
                            error_data = response.json()
                            error_code = error_data.get("error", "")
                            
                            if error_code == "authorization_pending":
                                # Still waiting
                                continue
                            elif error_code == "slow_down":
                                # Server asked to slow down
                                interval += 5
                                continue
                            elif error_code in ("expired_token", "access_denied"):
                                # Terminal errors
                                modal.set_status(f"Authentication failed: {error_code}", is_error=True)
                                raise Exception(f"Authentication {error_code}")
                            else:
                                # Unknown error
                                modal.set_status(f"Authentication error: {error_code}", is_error=True)
                                raise Exception(f"Authentication error: {error_code}")
                        else:
                            # Unexpected status code
                            modal.set_status(f"Unexpected response: {response.status_code}", is_error=True)
                            raise Exception(f"Unexpected status code: {response.status_code}")
                            
                    except httpx.HTTPError as e:
                        modal.set_status(f"Network error: {str(e)}", is_error=True)
                        raise
                        
        except Exception as e:
            error_msg = f"Login failed: {str(e)}"
            modal.set_status(error_msg, is_error=True)
            self.add_log(f"❌ {error_msg}", "ERROR")
            
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Login failed")
    
    @work(exclusive=True)
    async def perform_logout(self) -> None:
        """Perform logout and clear credentials"""
        if not self.ctx:
            self.add_log("❌ No context available for logout", "ERROR")
            self.notify("Cannot logout: No context available", severity="error")
            return
        
        try:
            existing_email = self._get_logged_in_email()
            
            if not existing_email:
                self.add_log("ℹ️  Not currently logged in", "INFO")
                self.notify("No active session found", severity="information")
                return
            
            # Clear the token cache
            clear_token_cache(self.ctx.obj.profile)

            self.add_log(
                f"✅ Successfully logged out user: {existing_email}",
                "SUCCESS"
            )
            self.notify(
                f"Logged out {existing_email}",
                severity="information",
                timeout=5
            )
            
            # Update the button
            self._update_auth_button()
            
        except Exception as e:
            error_msg = f"Logout failed: {str(e)}"
            self.add_log(f"❌ {error_msg}", "ERROR")
            self.notify(error_msg, severity="error", timeout=10)
            
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Logout failed")
    
    def open_remove_cluster_modal(self):
        """Open the cluster removal modal"""
        if not self.clusters:
            self.add_log("❌ No clusters available to remove", "WARNING")
            self.notify("No clusters available to remove", severity="warning")
            return
        
        def handle_cluster_removal(cluster_name: Optional[str]) -> None:
            """Handle the result from cluster removal modal"""
            if cluster_name:
                self.add_log(
                    f"🗑️  Removing cluster: {cluster_name}", 
                    "INFO"
                )
                # Remove the cluster via SDK (triggers async work)
                self.remove_cluster_from_modal(cluster_name)
            else:
                self.add_log("❌ Cluster removal cancelled", "INFO")
        
        # Push the modal screen and handle the result
        self.push_screen(RemoveClusterModal(self.clusters), handle_cluster_removal)
    
    @work(exclusive=True)
    async def remove_cluster_from_modal(self, cluster_name: str) -> None:
        """Remove a cluster using the SDK.
        
        This will:
        1. Find deployments associated with the cluster
        2. Remove those deployments (which will trigger app removal)
        3. Remove the cluster itself
        
        Args:
            cluster_name: Name of the cluster to remove
        """
        from vantage_cli.sdk.cluster.crud import cluster_sdk
        from vantage_cli.sdk.deployment.crud import deployment_sdk
        
        if not self.ctx:
            self.add_log("❌ No context available for cluster removal", "ERROR")
            self.notify("Cannot remove cluster: no context available", severity="error")
            return
        
        try:
            # Show removing status
            self.notify("Removing cluster...", severity="information")
            
            # Find the cluster object
            cluster = next((c for c in self.clusters if c.name == cluster_name), None)
            if not cluster:
                self.add_log(f"❌ Cluster '{cluster_name}' not found", "ERROR")
                self.notify(f"Cluster '{cluster_name}' not found", severity="error")
                return
            
            # Find deployments associated with this cluster
            associated_deployments = [
                dep for dep in self.deployments
                if dep.cluster.name == cluster_name
            ]
            
            # Remove deployments first
            if associated_deployments:
                self.add_log(
                    f"🔍 Found {len(associated_deployments)} deployment(s) using cluster '{cluster_name}'",
                    "INFO"
                )
                
                for deployment in associated_deployments:
                    try:
                        app_name = deployment.app_name
                        cloud = deployment.cloud
                        
                        self.add_log(
                            f"🗑️  Removing deployment '{deployment.name}' (app: {app_name})",
                            "INFO"
                        )
                        
                        # Try to call the app's remove function first
                        try:
                            # Dynamically import the app module
                            # Path format: vantage_cli.clouds.{cloud}.apps.{app_name}.app
                            app_module_path = f"vantage_cli.clouds.{cloud}.apps.{app_name}.app"
                            import importlib
                            app_module = importlib.import_module(app_module_path)
                            
                            if hasattr(app_module, 'remove'):
                                # Call the app's remove function
                                await app_module.remove(ctx=self.ctx, deployment=deployment)
                                self.add_log(
                                    f"✅ Successfully removed app '{app_name}' from deployment '{deployment.name}'",
                                    "SUCCESS"
                                )
                            else:
                                self.add_log(
                                    f"⚠️  App '{app_name}' does not have a remove function, skipping app cleanup",
                                    "WARNING"
                                )
                        except Exception as app_error:
                            self.add_log(
                                f"⚠️  Failed to remove app '{app_name}': {str(app_error)}",
                                "WARNING"
                            )
                        
                        # Delete the deployment from SDK storage
                        success = await deployment_sdk.delete(deployment_id=deployment.id)
                        
                        if success:
                            self.add_log(
                                f"✅ Successfully removed deployment '{deployment.name}'",
                                "SUCCESS"
                            )
                            # Remove from local deployments list
                            self.deployments = [d for d in self.deployments if d.id != deployment.id]
                        else:
                            self.add_log(
                                f"⚠️  Failed to remove deployment '{deployment.name}'",
                                "WARNING"
                            )
                    
                    except Exception as dep_error:
                        self.add_log(
                            f"⚠️  Error removing deployment '{deployment.name}': {str(dep_error)}",
                            "WARNING"
                        )
                        # Continue with cluster removal even if deployment removal fails
            
            # Remove the cluster
            self.add_log(f"🗑️  Removing cluster '{cluster_name}'", "INFO")
            success = await cluster_sdk.delete_cluster(
                ctx=self.ctx,
                cluster_name=cluster_name,
            )
            
            if success:
                self.add_log(
                    f"✅ Successfully removed cluster: {cluster_name}",
                    "SUCCESS"
                )
                
                self.notify(
                    f"Cluster '{cluster_name}' removed successfully!",
                    severity="information",
                    timeout=5
                )
                
                # Remove from local clusters list
                self.clusters = [c for c in self.clusters if c.name != cluster_name]
                
                # Refresh the clusters table if we're on the main dashboard
                try:
                    self.populate_clusters_table()
                except Exception:
                    pass
                
                # Notify the ClusterManagementTabPane to refresh if it exists
                try:
                    cluster_tab = self.query_one(ClusterManagementTabPane)
                    cluster_tab.refresh_clusters()
                except Exception:
                    pass
            else:
                raise Exception("Cluster deletion returned False")
                
        except Exception as e:
            error_msg = f"Failed to remove cluster: {str(e)}"
            self.add_log(f"❌ {error_msg}", "ERROR")
            self.notify(error_msg, severity="error", timeout=10)
            
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Cluster removal failed")

    # Action methods
    async def action_quit(self):
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
    
    The dashboard integrates with the Vantage CLI SDK to provide real-time
    monitoring and management of:
    - Clusters (vantage_cli.sdk.cluster)
    - Deployments (vantage_cli.sdk.deployment)
    - Profiles (vantage_cli.sdk.profile)
    
    Example:
        ```python
        from vantage_cli.sdk.cluster import cluster_sdk
        from vantage_cli.sdk.deployment import deployment_sdk
        from vantage_cli.dashboard import DashboardConfig, ServiceConfig, run_dashboard
        
        # Load data from SDK
        clusters = await cluster_sdk.list_clusters(ctx)
        deployments = await deployment_sdk.list(ctx)
        
        # Convert to services
        services = [ServiceConfig.from_cluster(c) for c in clusters]
        services += [ServiceConfig.from_deployment(d) for d in deployments]
        
        # Run dashboard
        config = DashboardConfig(title="My Dashboard")
        run_dashboard(config=config, services=services, ctx=ctx)
        ```
    
    Args:
        config: Dashboard configuration settings
        services: List of services to display (can use ServiceConfig.from_cluster/from_deployment)
        custom_handlers: Optional custom worker handler functions
        platform_info: Platform-specific URLs and information
        ctx: Typer context containing SDK client configuration
        setup_signals: Whether to setup signal handlers for graceful shutdown
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


# Export main dashboard classes and SDK schemas for convenience
__all__ = [
    # Dashboard classes
    "DashboardApp",
    "DashboardConfig",
    "ServiceConfig",
    "run_dashboard",
    # SDK schemas (re-exported for convenience)
    "Cluster",
    "Deployment",
    "Profile",
    "CliContext",
    # Tab panes
    "ClusterManagementTabPane",
    "DeploymentManagementTabPane",
    "ProfileManagementTabPane",
    # Worker tracking
    "Worker",
    "WorkerState",
    "DependencyTracker",
]
