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
"""Cluster Management TabPane for Dashboard.

A reusable TabPane widget for managing Vantage clusters in the dashboard.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import typer
from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label, Select, Static, TabPane

from vantage_cli.exceptions import Abort
from vantage_cli.sdk.cluster.crud import cluster_sdk
from vantage_cli.sdk.cluster.schema import Cluster

logger = logging.getLogger(__name__)


class CreateClusterModal(ModalScreen[Optional[Dict[str, str]]]):
    """Modal screen for creating a new cluster."""

    DEFAULT_CSS = """
    CreateClusterModal {
        align: center middle;
    }

    #create-cluster-dialog {
        width: 70;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #create-cluster-dialog .modal-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #create-cluster-dialog Label {
        margin-top: 1;
        color: $text;
    }

    #create-cluster-dialog Input {
        margin-bottom: 1;
    }

    #create-cluster-dialog Select {
        margin-bottom: 1;
    }

    #create-cluster-dialog #button-row {
        margin-top: 1;
        height: auto;
        align: center middle;
    }

    #create-cluster-dialog Button {
        margin: 0 1;
    }
    """

    def __init__(self, **kwargs):
        """Initialize the create cluster modal."""
        super().__init__(**kwargs)
        self.selected_cloud: Optional[str] = None

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="create-cluster-dialog"):
            yield Static("🖥️ Create New Cluster", classes="modal-title")

            yield Label("Cluster Name:")
            yield Input(
                placeholder="Enter cluster name (e.g., my-cluster)", id="cluster-name-input"
            )

            yield Label("Description (optional):")
            yield Input(placeholder="Enter cluster description", id="cluster-description-input")

            yield Label("Cloud Provider:")
            yield Select(
                options=[
                    ("AWS", "aws"),
                    ("GCP", "gcp"),
                    ("Azure", "azure"),
                    ("CUDO Compute", "cudo-compute"),
                    ("On-Premises", "on-premises"),
                    ("Kubernetes", "k8s"),
                    ("Localhost", "localhost"),
                ],
                prompt="Select cloud provider",
                id="cloud-provider-select",
            )

            yield Label("Deployment Application (optional):", id="app-label")
            yield Select(
                options=[],
                prompt="Select deployment application",
                id="deployment-app-select",
                disabled=True,
            )

            with Horizontal(id="button-row"):
                yield Button("✅ Create", variant="success", id="create-btn")
                yield Button("❌ Cancel", variant="error", id="cancel-btn")

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle cloud provider selection change to update deployment app options."""
        if event.select.id == "cloud-provider-select":
            selected_cloud = str(event.value) if event.value else None
            self.selected_cloud = selected_cloud

            # Update deployment app dropdown based on selected cloud
            if selected_cloud:
                self._update_deployment_apps(selected_cloud)
            else:
                # Disable deployment app dropdown if no cloud selected
                app_select = self.query_one("#deployment-app-select", Select)
                app_select.set_options([])
                app_select.disabled = True

    def _update_deployment_apps(self, cloud: str) -> None:
        """Update the deployment application dropdown based on selected cloud.

        Args:
            cloud: The selected cloud provider (e.g., 'localhost', 'aws')
        """
        try:
            # Import SDK here to avoid module-level initialization issues
            from vantage_cli.sdk.deployment_app import deployment_app_sdk

            # Get apps for the selected cloud
            apps = deployment_app_sdk.list(cloud=cloud)

            # Update the deployment app select widget
            app_select = self.query_one("#deployment-app-select", Select)

            if apps:
                # Create options from available apps
                app_options = [(f"{app.name} ({app.substrate})", app.name) for app in apps]
                app_select.set_options(app_options)
                app_select.disabled = False
                logger.debug(
                    f"Updated deployment apps for cloud '{cloud}': {[a.name for a in apps]}"
                )
            else:
                # No apps available for this cloud
                app_select.set_options([])
                app_select.disabled = True
                logger.debug(f"No deployment apps found for cloud '{cloud}'")

        except Exception as e:
            logger.error(f"Failed to load deployment apps for cloud '{cloud}': {e}")
            # Disable dropdown on error
            app_select = self.query_one("#deployment-app-select", Select)
            app_select.set_options([])
            app_select.disabled = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses in the modal."""
        if event.button.id == "create-btn":
            # Gather form data
            name_input = self.query_one("#cluster-name-input", Input)
            description_input = self.query_one("#cluster-description-input", Input)
            cloud_select = self.query_one("#cloud-provider-select", Select)
            app_select = self.query_one("#deployment-app-select", Select)

            cluster_name = name_input.value.strip()

            # Validate name
            if not cluster_name:
                self.notify("Cluster name is required", severity="error")
                return

            # Get deployment app if selected
            deployment_app = str(app_select.value) if app_select.value else None

            # Return the cluster data
            cluster_data = {
                "name": cluster_name,
                "description": description_input.value.strip(),
                "cloud": str(cloud_select.value) if cloud_select.value else "",
                "deployment_app": deployment_app,  # Include deployment app
            }

            self.dismiss(cluster_data)

        elif event.button.id == "cancel-btn":
            self.dismiss(None)


class RemoveClusterModal(ModalScreen[Optional[str]]):
    """Modal screen for removing a cluster."""

    DEFAULT_CSS = """
    RemoveClusterModal {
        align: center middle;
    }

    #remove-cluster-dialog {
        width: 70;
        height: auto;
        border: thick $error;
        background: $surface;
        padding: 1 2;
    }

    #remove-cluster-dialog .modal-title {
        text-align: center;
        text-style: bold;
        color: $error;
        margin-bottom: 1;
    }

    #remove-cluster-dialog .warning-text {
        text-align: center;
        color: $warning;
        margin-bottom: 1;
    }

    #remove-cluster-dialog Label {
        margin-top: 1;
        color: $text;
    }

    #remove-cluster-dialog Select {
        margin-bottom: 1;
    }

    #remove-cluster-dialog #button-row {
        margin-top: 1;
        height: auto;
        align: center middle;
    }

    #remove-cluster-dialog Button {
        margin: 0 1;
    }
    """

    def __init__(self, clusters: List[Cluster], **kwargs):
        """Initialize the remove cluster modal.

        Args:
            clusters: List of available clusters
            **kwargs: Additional arguments passed to parent widget
        """
        super().__init__(**kwargs)
        self.clusters = clusters

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="remove-cluster-dialog"):
            yield Static("🗑️  Remove Cluster", classes="modal-title")
            yield Static(
                "⚠️  Warning: This will remove the cluster and all associated deployments!",
                classes="warning-text",
            )

            yield Label("Select Cluster to Remove:")

            # Create dropdown options from clusters
            cluster_options = [
                (f"{cluster.name} ({cluster.provider})", cluster.name) for cluster in self.clusters
            ]

            if not cluster_options:
                yield Static("No clusters available to remove", classes="warning-text")
            else:
                yield Select(
                    options=cluster_options,
                    prompt="Select cluster to remove",
                    id="cluster-select",
                )

            with Horizontal(id="button-row"):
                yield Button(
                    "🗑️  Remove", variant="error", id="remove-btn", disabled=not cluster_options
                )
                yield Button("❌ Cancel", variant="primary", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses in the modal."""
        if event.button.id == "remove-btn":
            # Get selected cluster
            cluster_select = self.query_one("#cluster-select", Select)

            if not cluster_select.value:
                self.notify("Please select a cluster to remove", severity="error")
                return

            # Return the selected cluster name
            cluster_name = str(cluster_select.value)
            self.dismiss(cluster_name)

        elif event.button.id == "cancel-btn":
            self.dismiss(None)


class ClusterManagementTabPane(TabPane):
    """A TabPane widget for cluster management functionality."""

    DEFAULT_CSS = """
    ClusterManagementTabPane #cluster-filters {
        height: auto;
        padding: 0 1;
        margin: 0;
    }

    ClusterManagementTabPane #cluster-main-panel {
        height: 1fr;
        layout: horizontal;
        margin-top: 0;
        padding-top: 0;
    }

    ClusterManagementTabPane #clusters-panel {
        width: 1fr;
        height: 100%;
        padding: 0;
        border: solid $accent;
        border-title-align: center;
        border-title-color: $accent;
        border-title-background: $surface;
        overflow: auto;
    }

    ClusterManagementTabPane #cluster-detail-panel {
        width: 1fr;
        height: 100%;
        padding: 0;
        border: solid $accent;
        border-title-align: center;
        border-title-color: $accent;
        border-title-background: $surface;
        overflow: auto;
    }

    ClusterManagementTabPane #clusters-table {
        height: auto;
    }

    ClusterManagementTabPane #cluster-list-details {
        padding: 1;
        height: auto;
    }

    ClusterManagementTabPane #cluster-detail-panel {
        width: 1fr;
        height: 100%;
        padding: 0;
        border: solid $accent;
        border-title-align: center;
        border-title-color: $accent;
        border-title-background: $surface;
        overflow: auto;
    }

    ClusterManagementTabPane #cluster-detail-scroll {
        height: 100%;
    }

    ClusterManagementTabPane #cluster-detail {
        padding: 1;
        height: auto;
    }

    ClusterManagementTabPane #cluster-actions {
        height: auto;
        padding: 0 1;
        background: $surface;
    }

    ClusterManagementTabPane Button {
        min-width: 16;
    }
    """

    # Reactive attributes for cluster data
    clusters: reactive[List[Cluster]] = reactive([])
    selected_cluster: reactive[Optional[Cluster]] = reactive(None)
    is_loading: reactive[bool] = reactive(False)
    last_refresh: reactive[Optional[datetime]] = reactive(None)

    def __init__(self, ctx: typer.Context, **kwargs: Any) -> None:
        """Initialize the cluster management tab pane.

        Args:
            ctx: Typer context with settings and configuration
            **kwargs: Additional arguments passed to parent widget
        """
        super().__init__("🖥️ Clusters", id="clusters-tab", **kwargs)
        self.ctx = ctx

    def compose(self) -> ComposeResult:
        """Create the cluster management layout with 2-panel horizontal layout."""
        with Vertical():
            yield Static("🖥️ Cluster Management", classes="section-header")

            # Filters and refresh section
            with Horizontal(id="cluster-filters"):
                yield Button("🔄 Refresh", id="refresh-clusters-btn", variant="primary")

            # Main 2-panel horizontal layout
            with Horizontal(id="cluster-main-panel"):
                # Panel 1: Clusters List
                with Vertical(id="clusters-panel"):
                    # Action buttons for clusters
                    with Horizontal(id="cluster-actions"):
                        yield Button("➕ Create", id="create-cluster-btn", variant="success")
                        yield Button(
                            "🗑️ Remove", id="remove-cluster-btn", variant="error", disabled=True
                        )
                    yield DataTable(id="clusters-table", zebra_stripes=True, cursor_type="row")
                    yield Static("Select a cluster to view details", id="cluster-list-details")

                # Panel 2: Cluster Detail Viewer
                with Vertical(id="cluster-detail-panel"):
                    with ScrollableContainer(id="cluster-detail-scroll"):
                        yield Static("Select a cluster to view details", id="cluster-detail")

    def on_mount(self) -> None:
        """Initialize the cluster table when the tab is mounted."""
        self.setup_clusters_table()

        # Set border titles
        clusters_panel = self.query_one("#clusters-panel", Vertical)
        clusters_panel.border_title = "📋 Clusters"

        detail_panel = self.query_one("#cluster-detail-panel", Vertical)
        detail_panel.border_title = "📄 Cluster Details"

        # Debug the context structure
        logger.debug(f"ClusterManagementTabPane context: {self.ctx}")
        logger.debug(f"Context type: {type(self.ctx)}")
        if self.ctx and hasattr(self.ctx, "obj"):
            logger.debug(f"Context obj: {self.ctx.obj}")
            logger.debug(f"Context obj type: {type(self.ctx.obj)}")
            if hasattr(self.ctx.obj, "settings"):
                logger.debug(f"Settings found: {self.ctx.obj.settings}")
            else:
                logger.debug("No settings found in ctx.obj")
            if hasattr(self.ctx.obj, "profile"):
                logger.debug(f"Profile found: {self.ctx.obj.profile}")
            else:
                logger.debug("No profile found in ctx.obj")
        else:
            logger.debug("Context has no obj attribute")

        # Auto-refresh clusters on mount
        self.refresh_clusters()

    def setup_clusters_table(self) -> None:
        """Set up the clusters table with columns."""
        table = self.query_one("#clusters-table", DataTable)
        table.add_columns("Name", "Status", "Provider", "Owner", "Description")
        table.cursor_type = "row"
        table.show_cursor = True
        logger.debug(
            f"Clusters table setup complete. cursor_type={table.cursor_type}, show_cursor={table.show_cursor}"
        )

    @work(exclusive=True)
    async def refresh_clusters(self) -> None:
        """Refresh the clusters list from the API."""
        self.is_loading = True

        try:
            # Fetch clusters using the SDK
            logger.debug("Starting cluster refresh...")
            clusters_data = await cluster_sdk.list_clusters(self.ctx)
            logger.debug(f"Fetched {len(clusters_data)} clusters")

            self.clusters = clusters_data
            self.last_refresh = datetime.now()

            # Update the UI
            self.update_clusters_table()

            logger.debug("Cluster refresh completed successfully")
            self.notify(f"Loaded {len(clusters_data)} clusters", severity="information")

        except Abort as e:
            error_msg = f"Failed to fetch clusters: {e.message}"
            logger.error(error_msg)
            self.notify(error_msg, severity="error")

        except Exception as e:
            error_msg = f"Unexpected error fetching clusters: {str(e)}"
            logger.error(error_msg)
            logger.exception("Full traceback:")
            self.notify(error_msg, severity="error")

        finally:
            self.is_loading = False

    def update_clusters_table(self) -> None:
        """Update the clusters table with current data."""
        table = self.query_one("#clusters-table", DataTable)
        table.clear()

        logger.debug(f"Updating clusters table with {len(self.clusters)} clusters")

        if not self.clusters:
            logger.debug("No clusters to display")
            return

        for cluster in self.clusters:
            logger.debug(f"Processing cluster: {cluster}")

            # Extract key information for the table
            name = cluster.name
            status = cluster.status
            provider = cluster.provider if cluster.provider else "Unknown"
            owner = cluster.owner_email if cluster.owner_email else "Unknown"
            description = cluster.description if cluster.description else "No description"

            # Truncate long descriptions
            if len(description) > 50:
                description = description[:47] + "..."

            logger.debug(f"Adding row: {name}, {status}, {provider}, {owner}, {description}")
            table.add_row(name, status, provider, owner, description, key=name)

    def update_cluster_details(self, cluster: Cluster) -> None:
        """Update the cluster details view with selected cluster info."""
        detail_widget = self.query_one("#cluster-detail", Static)

        # Convert cluster to dict for display
        cluster_dict = cluster.model_dump() if hasattr(cluster, "model_dump") else cluster.__dict__

        # Build detail text
        detail_text = f"[bold]Cluster:[/bold] {cluster.name}\n\n"

        # Display all cluster properties
        for key, value in cluster_dict.items():
            if value is not None and key != "name":  # Skip name since it's in the header
                # Format the key for display
                display_key = key.replace("_", " ").replace("Id", " ID").title()
                detail_text += f"[bold]{display_key}:[/bold] {value}\n"

        detail_widget.update(detail_text)

    def enable_cluster_actions(self, enabled: bool) -> None:
        """Enable or disable cluster action buttons."""
        create_btn = self.query_one("#create-cluster-btn", Button)
        remove_btn = self.query_one("#remove-cluster-btn", Button)

        create_btn.disabled = False  # Create is always enabled
        remove_btn.disabled = not enabled

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle cluster selection in the table."""
        logger.debug(
            f"Row selected event: table_id={event.data_table.id}, row_key={event.row_key}"
        )

        if event.data_table.id == "clusters-table":
            cluster_name = event.row_key
            logger.debug(f"Cluster selected: {cluster_name}")

            # Find the selected cluster
            selected = next(
                (cluster for cluster in self.clusters if cluster.name == cluster_name), None
            )

            if selected:
                logger.debug(f"Found cluster data for {cluster_name}: {selected}")
                self.selected_cluster = selected
                self.update_cluster_details(selected)
                self.enable_cluster_actions(True)
                self.notify(f"Selected cluster: {cluster_name}")
            else:
                logger.warning(f"Could not find cluster data for {cluster_name}")
        else:
            logger.debug(f"Row selection from different table: {event.data_table.id}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "refresh-clusters-btn":
            self.refresh_clusters()

        elif event.button.id == "create-cluster-btn":
            # TODO: Open create cluster modal
            self.notify("Create cluster functionality coming soon", severity="information")

        elif event.button.id == "remove-cluster-btn" and self.selected_cluster:
            # TODO: Open remove cluster modal
            self.notify(f"Remove cluster: {self.selected_cluster.name}", severity="warning")
