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
"""Cluster Management TabPane for Dashboard

A reusable TabPane widget for managing Vantage clusters in the dashboard.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import typer
import logging

logger = logging.getLogger(__name__)
from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Button, DataTable, Static, TabPane

from vantage_cli.exceptions import Abort
from vantage_cli.sdk.cluster import get as get_cluster
from vantage_cli.sdk.cluster import list as list_clusters


class ClusterManagementTabPane(TabPane):
    """A TabPane widget for cluster management functionality."""

    # Reactive attributes for cluster data
    clusters: reactive[List[Dict[str, Any]]] = reactive([])
    selected_cluster: reactive[Optional[Dict[str, Any]]] = reactive(None)
    is_loading: reactive[bool] = reactive(False)
    last_refresh: reactive[Optional[datetime]] = reactive(None)

    def __init__(self, ctx: typer.Context, **kwargs: Any) -> None:
        """Initialize the cluster management tab pane.

        Args:
            ctx: Typer context with settings and configuration
        """
        super().__init__("🖥️ Clusters", id="clusters-tab", **kwargs)
        self.ctx = ctx

    def compose(self) -> ComposeResult:
        """Create the cluster management layout."""
        with Vertical():
            yield Static("🖥️ Cluster Management", classes="section-header")

            # Status and refresh section
            with Horizontal(id="cluster-status-bar"):
                yield Static("Status: Ready", id="cluster-status")
                yield Static("Last refresh: Never", id="last-refresh-display")
                yield Button("🔄 Refresh", id="refresh-clusters-btn", variant="primary")

            # Clusters table
            with Vertical(id="clusters-section"):
                yield Static("📋 Available Clusters", classes="subsection-header")
                yield DataTable(id="clusters-table", zebra_stripes=True)

            # Selected cluster details
            with Vertical(id="cluster-details-section"):
                yield Static("📄 Cluster Details", classes="subsection-header")
                yield DataTable(id="cluster-details-table")

            # Action buttons
            with Horizontal(id="cluster-actions"):
                yield Button("📊 View Details", id="view-details-btn", disabled=True)
                yield Button("🔄 Refresh Status", id="refresh-status-btn", disabled=True)
                yield Button("⚙️ Manage", id="manage-cluster-btn", disabled=True)

    def on_mount(self) -> None:
        """Initialize the cluster table when the tab is mounted."""
        self.setup_clusters_table()
        self.setup_details_table()

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
        """Setup the clusters table with columns."""
        table = self.query_one("#clusters-table", DataTable)
        table.add_columns("Name", "Status", "Provider", "Owner", "Description")
        table.cursor_type = "row"
        table.show_cursor = True
        logger.debug(
            f"Clusters table setup complete. cursor_type={table.cursor_type}, show_cursor={table.show_cursor}"
        )

    def setup_details_table(self) -> None:
        """Setup the cluster details table."""
        details_table = self.query_one("#cluster-details-table", DataTable)
        details_table.add_columns("Property", "Value")

    @work(exclusive=True)
    async def refresh_clusters(self) -> None:
        """Refresh the clusters list from the API."""
        self.is_loading = True
        status_widget = self.query_one("#cluster-status", Static)
        status_widget.update("Status: Loading clusters...")

        try:
            # Fetch clusters using the SDK
            logger.debug("Starting cluster refresh...")
            clusters_data = await list_clusters(self.ctx)
            logger.debug(f"Fetched {len(clusters_data)} clusters")

            self.clusters = clusters_data
            self.last_refresh = datetime.now()

            # Update the UI
            self.update_clusters_table()
            self.update_status_display()

            logger.debug("Cluster refresh completed successfully")

        except Abort as e:
            error_msg = f"Failed to fetch clusters: {e.message}"
            logger.error(error_msg)
            status_widget.update(f"Status: Error - {e.message}")
            # Show notification to user
            self.notify(error_msg, severity="error")

        except Exception as e:
            error_msg = f"Unexpected error fetching clusters: {str(e)}"
            logger.error(error_msg)
            logger.exception("Full traceback:")
            status_widget.update(f"Status: Unexpected error - {str(e)}")
            # Show notification to user
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

        for i, cluster in enumerate(self.clusters):
            logger.debug(f"Processing cluster {i}: {cluster}")

            # Extract key information for the table
            name = cluster.get("name", "Unknown")
            status = cluster.get("status", "Unknown")
            provider = cluster.get("provider", "Unknown")
            owner = cluster.get("ownerEmail", "Unknown")
            description = cluster.get("description", "No description")

            # Truncate long descriptions
            if len(description) > 50:
                description = description[:47] + "..."

            logger.debug(f"Adding row: {name}, {status}, {provider}, {owner}, {description}")
            table.add_row(name, status, provider, owner, description, key=name)

    def update_status_display(self) -> None:
        """Update the status and last refresh display."""
        status_widget = self.query_one("#cluster-status", Static)
        refresh_widget = self.query_one("#last-refresh-display", Static)

        cluster_count = len(self.clusters)
        status_widget.update(f"Status: Ready ({cluster_count} clusters)")

        if self.last_refresh:
            refresh_time = self.last_refresh.strftime("%H:%M:%S")
            refresh_widget.update(f"Last refresh: {refresh_time}")

    def update_cluster_details(self, cluster: Dict[str, Any]) -> None:
        """Update the cluster details table with selected cluster info."""
        details_table = self.query_one("#cluster-details-table", DataTable)
        details_table.clear()

        # Display all cluster properties
        for key, value in cluster.items():
            if value is not None:
                # Format the key for display
                display_key = key.replace("_", " ").replace("Id", " ID").title()
                details_table.add_row(display_key, str(value))

    def enable_cluster_actions(self, enabled: bool) -> None:
        """Enable or disable cluster action buttons."""
        view_btn = self.query_one("#view-details-btn", Button)
        refresh_btn = self.query_one("#refresh-status-btn", Button)
        manage_btn = self.query_one("#manage-cluster-btn", Button)

        view_btn.disabled = not enabled
        refresh_btn.disabled = not enabled
        manage_btn.disabled = not enabled

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
                (cluster for cluster in self.clusters if cluster.get("name") == cluster_name), None
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

        elif event.button.id == "view-details-btn" and self.selected_cluster:
            # Could open a detailed view or modal
            self.notify(f"Viewing details for {self.selected_cluster.get('name')}")

        elif event.button.id == "refresh-status-btn" and self.selected_cluster:
            # Refresh the specific cluster's status
            self.refresh_cluster_status()

        elif event.button.id == "manage-cluster-btn" and self.selected_cluster:
            # Could open cluster management actions
            self.notify(f"Managing cluster {self.selected_cluster.get('name')}")

    @work(exclusive=True)
    async def refresh_cluster_status(self) -> None:
        """Refresh the status of the selected cluster."""
        if not self.selected_cluster:
            return

        cluster_name = self.selected_cluster.get("name")
        if not cluster_name:
            return

        try:
            # Fetch updated cluster details
            updated_cluster = await get_cluster(self.ctx, cluster_name)

            if updated_cluster:
                # Update the cluster in our list
                for i, cluster in enumerate(self.clusters):
                    if cluster.get("name") == cluster_name:
                        self.clusters[i] = updated_cluster
                        break

                self.selected_cluster = updated_cluster
                self.update_clusters_table()
                self.update_cluster_details(updated_cluster)
                self.notify(f"Refreshed status for {cluster_name}")
            else:
                self.notify(f"Cluster {cluster_name} not found", severity="warning")

        except Exception as e:
            logger.error(f"Failed to refresh cluster status: {e}")
            self.notify(f"Failed to refresh cluster status: {str(e)}", severity="error")
