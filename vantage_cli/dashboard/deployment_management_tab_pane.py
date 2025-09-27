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
"""Deployment Management TabPane for Dashboard.

A reusable TabPane widget for managing Vantage deployments in the dashboard.
"""

import logging
from datetime import datetime
from typing import Any, List, Optional

import typer
from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, DataTable, Select, Static, TabPane

from vantage_cli.exceptions import Abort
from vantage_cli.sdk.deployment import deployment_sdk
from vantage_cli.sdk.deployment.schema import Deployment

logger = logging.getLogger(__name__)


class DeploymentObjectReceived(Message):
    """Message sent when a deployment object is received from the SDK."""

    def __init__(self, deployment: Deployment) -> None:
        self.deployment = deployment
        super().__init__()


class DeploymentManagementTabPane(TabPane):
    """A TabPane widget for deployment management functionality."""

    DEFAULT_CSS = """
    DeploymentManagementTabPane #deployment-filters {
        height: auto;
        padding: 0 1;
        margin: 0;
    }

    DeploymentManagementTabPane #deployment-main-panel {
        height: 1fr;
        layout: horizontal;
        margin-top: 0;
        padding-top: 0;
    }

    DeploymentManagementTabPane #deployments-panel {
        width: 1fr;
        height: 100%;
        padding: 0;
        border: solid $accent;
        border-title-align: center;
        border-title-color: $accent;
        border-title-background: $surface;
        overflow: auto;
    }

    DeploymentManagementTabPane #deployments-table {
        height: auto;
    }

    DeploymentManagementTabPane #deployment-list-details {
        padding: 1;
        height: auto;
    }

    DeploymentManagementTabPane #deployment-detail-panel {
        width: 1fr;
        height: 100%;
        padding: 0;
        border: solid $accent;
        border-title-align: center;
        border-title-color: $accent;
        border-title-background: $surface;
        overflow: auto;
    }

    DeploymentManagementTabPane #deployment-detail-scroll {
        height: 100%;
    }

    DeploymentManagementTabPane #deployment-detail {
        padding: 1;
        height: auto;
    }

    DeploymentManagementTabPane #deployment-actions {
        height: auto;
        padding: 0 1;
        background: $surface;
    }

    DeploymentManagementTabPane Button {
        min-width: 16;
    }
    """

    # Reactive attributes for deployment data
    deployments: reactive[List[Deployment]] = reactive([])
    selected_deployment: reactive[Optional[Deployment]] = reactive(None)
    is_loading: reactive[bool] = reactive(False)
    last_refresh: reactive[Optional[datetime]] = reactive(None)
    cloud_filter: reactive[str] = reactive("all")
    status_filter: reactive[str] = reactive("all")

    def __init__(self, ctx: typer.Context, **kwargs: Any) -> None:
        """Initialize the deployment management tab pane.

        Args:
            ctx: Typer context with settings and configuration
            **kwargs: Additional arguments passed to parent widget
        """
        super().__init__("🚀 Deployments", id="deployments-tab", **kwargs)
        self.ctx = ctx

    def compose(self) -> ComposeResult:
        """Create the deployment management layout with 2-panel horizontal layout."""
        with Vertical():
            yield Static("🚀 Deployment Management", classes="section-header")

            # Filters and refresh section
            with Horizontal(id="deployment-filters"):
                yield Select(
                    [("All Clouds", "all"), ("AWS", "aws"), ("GCP", "gcp"), ("Azure", "azure")],
                    prompt="Cloud:",
                    value="all",
                    id="cloud-filter-select",
                )
                yield Select(
                    [
                        ("All Status", "all"),
                        ("Active", "active"),
                        ("Inactive", "inactive"),
                        ("Error", "error"),
                    ],
                    prompt="Status:",
                    value="all",
                    id="status-filter-select",
                )
                yield Button("🔄 Refresh", id="refresh-deployments-btn", variant="primary")

            # Main 2-panel horizontal layout
            with Horizontal(id="deployment-main-panel"):
                # Panel 1: Deployments List
                with Vertical(id="deployments-panel"):
                    # Action buttons for deployments
                    with Horizontal(id="deployment-actions"):
                        yield Button("➕ Create", id="create-deployment-btn", variant="success")
                        yield Button(
                            "🛑 Stop", id="stop-deployment-btn", variant="warning", disabled=True
                        )
                        yield Button(
                            "🗑️ Delete", id="delete-deployment-btn", variant="error", disabled=True
                        )
                    yield DataTable(id="deployments-table", zebra_stripes=True, cursor_type="row")
                    yield Static(
                        "Select a deployment to view details", id="deployment-list-details"
                    )

                # Panel 2: Deployment Detail Viewer
                with Vertical(id="deployment-detail-panel"):
                    with ScrollableContainer(id="deployment-detail-scroll"):
                        yield Static("Select a deployment to view details", id="deployment-detail")

    def on_mount(self) -> None:
        """Initialize the deployment table when the tab is mounted."""
        # Set border titles for panels
        deployments_panel = self.query_one("#deployments-panel", Vertical)
        deployments_panel.border_title = "Deployments"

        detail_panel = self.query_one("#deployment-detail-panel", Vertical)
        detail_panel.border_title = "Deployment Details"

        self.setup_deployments_table()

        # Debug the context structure
        logger.debug(f"DeploymentManagementTabPane context: {self.ctx}")

        # Auto-refresh deployments on mount
        self.refresh_deployments()

    def setup_deployments_table(self) -> None:
        """Set up the deployments table with columns."""
        table = self.query_one("#deployments-table", DataTable)
        table.add_columns("Name", "App", "Cluster", "Cloud", "Status", "Created", "Active")
        table.cursor_type = "row"
        table.show_cursor = True
        logger.debug("Deployments table setup complete.")

    @work(exclusive=True)
    async def refresh_deployments(self) -> None:
        """Refresh the deployments list from the local storage."""
        self.is_loading = True

        try:
            # Fetch deployments using the SDK
            logger.debug("Starting deployment refresh...")

            # Apply filters based on current selection
            filter_kwargs = {}
            if self.cloud_filter != "all":
                filter_kwargs["cloud"] = self.cloud_filter
            # Always pass status filter (including "all")
            filter_kwargs["status"] = self.status_filter

            # Get deployments as Deployment objects
            deployments_data = await deployment_sdk.list_deployments(self.ctx, **filter_kwargs)
            logger.debug(f"Fetched {len(deployments_data)} deployments")

            self.deployments = deployments_data
            self.last_refresh = datetime.now()

            # Update the UI
            self.update_deployments_table()

            logger.debug("Deployment refresh completed successfully")
            self.notify(f"Loaded {len(deployments_data)} deployments", severity="information")

        except Abort as e:
            error_msg = f"Failed to fetch deployments: {e.message}"
            logger.error(error_msg)
            self.notify(error_msg, severity="error")

        except Exception as e:
            error_msg = f"Unexpected error fetching deployments: {str(e)}"
            logger.error(error_msg)
            logger.exception("Full traceback:")
            self.notify(error_msg, severity="error")

        finally:
            self.is_loading = False

    def update_deployments_table(self) -> None:
        """Update the deployments table with current data."""
        table = self.query_one("#deployments-table", DataTable)
        table.clear()

        logger.debug(f"Updating deployments table with {len(self.deployments)} deployments")

        if not self.deployments:
            logger.debug("No deployments to display")
            return

        for i, deployment in enumerate(self.deployments):
            logger.debug(f"Processing deployment {i}: {deployment.id}")

            # Use the Deployment schema object properties
            name = deployment.name
            app_name = deployment.app_name
            cluster_name = deployment.cluster_name
            cloud_name = (
                deployment.cloud.name
                if hasattr(deployment.cloud, "name")
                else str(deployment.cloud)
            )
            cloud = cloud_name.upper() if cloud_name else "Unknown"
            status = deployment.status
            created = deployment.formatted_created_at  # Using computed field
            is_active = "✅" if deployment.is_active else "❌"  # Using computed field

            logger.debug(
                f"Adding row: {name}, {app_name}, {cluster_name}, {cloud}, {status}, {created}, {is_active}"
            )
            table.add_row(
                name,
                app_name,
                cluster_name,
                cloud,
                status,
                created,
                is_active,
                key=deployment.id,
            )

    def update_deployment_details(self, deployment: Deployment) -> None:
        """Update the deployment details viewer with selected deployment info."""
        # Show loading message
        detail_widget = self.query_one("#deployment-detail", Static)
        detail_widget.update("Loading deployment details...")

        # Use an async worker to get the deployment object from the SDK
        self.run_worker(self._fetch_deployment_object(deployment.id), exclusive=True)

    async def _fetch_deployment_object(self, deployment_id: str) -> None:
        """Fetch deployment object from the SDK."""
        try:
            # Get the deployment object from the SDK using get_deployment()
            deployment = await deployment_sdk.get_deployment(self.ctx, deployment_id)

            if deployment:
                # Post the deployment object back to the main thread
                self.post_message(DeploymentObjectReceived(deployment))
            else:
                logger.warning(f"No deployment found for {deployment_id}")
                self.notify(f"Could not load deployment {deployment_id}", severity="warning")
        except Exception as e:
            logger.error(f"Failed to fetch deployment: {e}")
            self.notify(f"Error loading deployment: {e}", severity="error")

    def _display_deployment_object(self, deployment: Deployment) -> None:
        """Display deployment object properties in the details viewer."""
        from rich.markup import escape
        from rich.table import Table

        # Create Rich table for details
        details_table = Table(show_header=False, box=None, padding=(0, 1))
        details_table.add_column("Property", style="bold cyan", no_wrap=True)
        details_table.add_column("Value", style="white")

        # Display all the deployment object properties from the schema
        display_items = [
            ("Deployment ID", deployment.id),
            ("Deployment Name", deployment.name),
            ("App Name", deployment.app_name),
            ("Cluster Name", deployment.cluster_name),
            ("Cluster ID", deployment.cluster_id),
            (
                "Cloud Provider",
                deployment.cloud.name.upper()
                if hasattr(deployment.cloud, "name")
                else str(deployment.cloud).upper(),
            ),
            ("Status", deployment.status),
            ("Created At", deployment.formatted_created_at),
            ("Is Active", "✅ Yes" if deployment.is_active else "❌ No"),
            (
                "Compatible Integrations",
                ", ".join(deployment.compatible_integrations)
                if deployment.compatible_integrations
                else "None",
            ),
        ]

        # Add all items to the table
        for key, value in display_items:
            details_table.add_row(key, escape(str(value)))

        # Update the Static widget
        detail_widget = self.query_one("#deployment-detail", Static)
        detail_widget.update(details_table)

    def on_deployment_object_received(self, message: DeploymentObjectReceived) -> None:
        """Handle received deployment object."""
        self._display_deployment_object(message.deployment)

    def enable_deployment_actions(self, enabled: bool) -> None:
        """Enable or disable deployment action buttons."""
        stop_btn = self.query_one("#stop-deployment-btn", Button)
        delete_btn = self.query_one("#delete-deployment-btn", Button)

        stop_btn.disabled = not enabled
        delete_btn.disabled = not enabled

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle deployment selection in the table."""
        logger.debug(
            f"Row selected event: table_id={event.data_table.id}, row_key={event.row_key}"
        )

        if event.data_table.id == "deployments-table":
            deployment_id = event.row_key
            logger.debug(f"Deployment selected: {deployment_id}")

            # Find the selected deployment
            selected = next(
                (deployment for deployment in self.deployments if deployment.id == deployment_id),
                None,
            )

            if selected:
                logger.debug(f"Found deployment data for {deployment_id}: {selected}")
                self.selected_deployment = selected
                self.update_deployment_details(selected)
                self.enable_deployment_actions(True)
                self.notify(f"Selected deployment: {selected.name}")
            else:
                logger.warning(f"Could not find deployment data for {deployment_id}")
        else:
            logger.debug(f"Row selection from different table: {event.data_table.id}")

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle filter changes."""
        if event.select.id == "cloud-filter-select":
            if isinstance(event.value, str):
                self.cloud_filter = event.value
                logger.debug(f"Cloud filter changed to: {event.value}")
                self.refresh_deployments()

        elif event.select.id == "status-filter-select":
            if isinstance(event.value, str):
                self.status_filter = event.value
                logger.debug(f"Status filter changed to: {event.value}")
                self.refresh_deployments()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "refresh-deployments-btn":
            self.refresh_deployments()

        elif event.button.id == "view-deployment-details-btn" and self.selected_deployment:
            self.notify(f"Viewing details for {self.selected_deployment.name}")

        elif event.button.id == "refresh-deployment-status-btn" and self.selected_deployment:
            self.refresh_deployment_status()

        elif event.button.id == "manage-deployment-btn" and self.selected_deployment:
            self.notify(f"Managing deployment {self.selected_deployment.name}")

        elif event.button.id == "delete-deployment-btn" and self.selected_deployment:
            self.delete_deployment()

    @work(exclusive=True)
    async def refresh_deployment_status(self) -> None:
        """Refresh the status of the selected deployment."""
        if not self.selected_deployment:
            return

        deployment_id = self.selected_deployment.id

        try:
            # Fetch updated deployment object
            updated_deployment = await deployment_sdk.get_deployment(self.ctx, deployment_id)

            if updated_deployment:
                # Update the deployment in our list
                for i, deployment in enumerate(self.deployments):
                    if deployment.id == deployment_id:
                        self.deployments[i] = updated_deployment
                        break

                self.selected_deployment = updated_deployment
                self.update_deployments_table()
                self.update_deployment_details(updated_deployment)
                self.notify(f"Refreshed status for {updated_deployment.name}")
            else:
                self.notify(f"Deployment {deployment_id} not found", severity="warning")

        except Exception as e:
            logger.error(f"Failed to refresh deployment status: {e}")
            self.notify(f"Failed to refresh deployment status: {str(e)}", severity="error")

    @work(exclusive=True)
    async def delete_deployment(self) -> None:
        """Delete the selected deployment."""
        if not self.selected_deployment:
            return

        deployment_id = self.selected_deployment.id
        deployment_name = self.selected_deployment.name

        try:
            # Delete the deployment using the SDK
            success = await deployment_sdk.delete(deployment_id)

            if success:
                # Remove from our list
                self.deployments = [d for d in self.deployments if d.id != deployment_id]
                self.selected_deployment = None
                self.update_deployments_table()
                self.enable_deployment_actions(False)

                # Clear details viewer
                detail_widget = self.query_one("#deployment-detail", Static)
                detail_widget.update("Select a deployment to view details")

                self.notify(f"Deleted deployment: {deployment_name}")
            else:
                self.notify(f"Failed to delete deployment: {deployment_name}", severity="error")

        except Exception as e:
            logger.error(f"Failed to delete deployment: {e}")
            self.notify(f"Failed to delete deployment: {str(e)}", severity="error")
