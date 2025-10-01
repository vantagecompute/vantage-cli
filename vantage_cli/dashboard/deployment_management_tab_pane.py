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
"""Deployment Management TabPane for Dashboard

A reusable TabPane widget for managing Vantage deployments in the dashboard.
"""

from datetime import datetime
from typing import Any, List, Optional

import typer
from loguru import logger
from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, DataTable, Select, Static, TabPane

from vantage_cli.exceptions import Abort
from vantage_cli.sdk.deployment.schema import Deployment
from vantage_cli.sdk.deployment import deployment_sdk


class DeploymentObjectReceived(Message):
    """Message sent when a deployment object is received from the SDK."""

    def __init__(self, deployment: Deployment) -> None:
        self.deployment = deployment
        super().__init__()


class DeploymentManagementTabPane(TabPane):
    """A TabPane widget for deployment management functionality."""

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
        """
        super().__init__("🚀 Deployments", id="deployments-tab", **kwargs)
        self.ctx = ctx

    def compose(self) -> ComposeResult:
        """Create the deployment management layout."""
        with Vertical():
            yield Static("🚀 Deployment Management", classes="section-header")

            # Status and controls section
            with Horizontal(id="deployment-status-bar"):
                yield Static("Status: Ready", id="deployment-status")
                yield Static("Last refresh: Never", id="deployment-last-refresh-display")

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

            # Deployments table
            with Vertical(id="deployments-section"):
                yield Static("📋 Available Deployments", classes="subsection-header")
                yield DataTable(id="deployments-table", zebra_stripes=True)

            # Selected deployment details
            with Vertical(id="deployment-details-section"):
                yield Static("📄 Deployment Details", classes="subsection-header")
                yield DataTable(id="deployment-details-table")

            # Action buttons
            with Horizontal(id="deployment-actions"):
                yield Button("📊 View Details", id="view-deployment-details-btn", disabled=True)
                yield Button(
                    "🔄 Refresh Status", id="refresh-deployment-status-btn", disabled=True
                )
                yield Button("⚙️ Manage", id="manage-deployment-btn", disabled=True)
                yield Button(
                    "🗑️ Delete", id="delete-deployment-btn", disabled=True, variant="error"
                )

    def on_mount(self) -> None:
        """Initialize the deployment table when the tab is mounted."""
        self.setup_deployments_table()
        self.setup_details_table()

        # Debug the context structure
        logger.debug(f"DeploymentManagementTabPane context: {self.ctx}")

        # Auto-refresh deployments on mount
        self.refresh_deployments()

    def setup_deployments_table(self) -> None:
        """Setup the deployments table with columns."""
        table = self.query_one("#deployments-table", DataTable)
        table.add_columns("Name", "App", "Cluster", "Cloud", "Status", "Created", "Active")
        table.cursor_type = "row"
        table.show_cursor = True
        logger.debug("Deployments table setup complete.")

    def setup_details_table(self) -> None:
        """Setup the deployment details table."""
        details_table = self.query_one("#deployment-details-table", DataTable)
        details_table.add_columns("Property", "Value")

    @work(exclusive=True)
    async def refresh_deployments(self) -> None:
        """Refresh the deployments list from the local storage."""
        self.is_loading = True
        status_widget = self.query_one("#deployment-status", Static)
        status_widget.update("Status: Loading deployments...")

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
            self.update_status_display()

            logger.debug("Deployment refresh completed successfully")

        except Abort as e:
            error_msg = f"Failed to fetch deployments: {e.message}"
            logger.error(error_msg)
            status_widget.update(f"Status: Error - {e.message}")
            self.notify(error_msg, severity="error")

        except Exception as e:
            error_msg = f"Unexpected error fetching deployments: {str(e)}"
            logger.error(error_msg)
            logger.exception("Full traceback:")
            status_widget.update(f"Status: Unexpected error - {str(e)}")
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
            logger.debug(f"Processing deployment {i}: {deployment.deployment_id}")

            # Use the Deployment schema object properties
            name = deployment.deployment_name
            app_name = deployment.app_name
            cluster_name = deployment.cluster_name
            cloud = deployment.cloud.upper() if deployment.cloud else "Unknown"
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
                key=deployment.deployment_id,
            )

    def update_status_display(self) -> None:
        """Update the status and last refresh display."""
        status_widget = self.query_one("#deployment-status", Static)
        refresh_widget = self.query_one("#deployment-last-refresh-display", Static)

        deployment_count = len(self.deployments)
        active_count = sum(1 for d in self.deployments if d.is_active)
        status_widget.update(
            f"Status: Ready ({deployment_count} deployments, {active_count} active)"
        )

        if self.last_refresh:
            refresh_time = self.last_refresh.strftime("%H:%M:%S")
            refresh_widget.update(f"Last refresh: {refresh_time}")

    def update_deployment_details(self, deployment: Deployment) -> None:
        """Update the deployment details table with selected deployment info."""
        details_table = self.query_one("#deployment-details-table", DataTable)
        details_table.clear()

        # Show loading message
        details_table.add_row("Status", "Loading deployment details...")

        # Use an async worker to get the deployment object from the SDK
        self.run_worker(self._fetch_deployment_object(deployment.deployment_id), exclusive=True)

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
        """Display deployment object properties in the details table."""
        details_table = self.query_one("#deployment-details-table", DataTable)
        details_table.clear()

        # Display all the deployment object properties from the schema
        display_items = [
            ("Deployment ID", deployment.deployment_id),
            ("Deployment Name", deployment.deployment_name),
            ("App Name", deployment.app_name),
            ("Cluster Name", deployment.cluster_name),
            ("Cluster ID", deployment.cluster_id),
            ("Cloud Provider", deployment.cloud.upper() if deployment.cloud else "Unknown"),
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
            details_table.add_row(key, str(value))

    def on_deployment_object_received(self, message: DeploymentObjectReceived) -> None:
        """Handle received deployment object."""
        self._display_deployment_object(message.deployment)

    def enable_deployment_actions(self, enabled: bool) -> None:
        """Enable or disable deployment action buttons."""
        view_btn = self.query_one("#view-deployment-details-btn", Button)
        refresh_btn = self.query_one("#refresh-deployment-status-btn", Button)
        manage_btn = self.query_one("#manage-deployment-btn", Button)
        delete_btn = self.query_one("#delete-deployment-btn", Button)

        view_btn.disabled = not enabled
        refresh_btn.disabled = not enabled
        manage_btn.disabled = not enabled
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
                (
                    deployment
                    for deployment in self.deployments
                    if deployment.deployment_id == deployment_id
                ),
                None,
            )

            if selected:
                logger.debug(f"Found deployment data for {deployment_id}: {selected}")
                self.selected_deployment = selected
                self.update_deployment_details(selected)
                self.enable_deployment_actions(True)
                self.notify(f"Selected deployment: {selected.deployment_name}")
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
            self.notify(f"Viewing details for {self.selected_deployment.deployment_name}")

        elif event.button.id == "refresh-deployment-status-btn" and self.selected_deployment:
            self.refresh_deployment_status()

        elif event.button.id == "manage-deployment-btn" and self.selected_deployment:
            self.notify(f"Managing deployment {self.selected_deployment.deployment_name}")

        elif event.button.id == "delete-deployment-btn" and self.selected_deployment:
            self.delete_deployment()

    @work(exclusive=True)
    async def refresh_deployment_status(self) -> None:
        """Refresh the status of the selected deployment."""
        if not self.selected_deployment:
            return

        deployment_id = self.selected_deployment.deployment_id

        try:
            # Fetch updated deployment object
            updated_deployment = await deployment_sdk.get_deployment(self.ctx, deployment_id)

            if updated_deployment:
                # Update the deployment in our list
                for i, deployment in enumerate(self.deployments):
                    if deployment.deployment_id == deployment_id:
                        self.deployments[i] = updated_deployment
                        break

                self.selected_deployment = updated_deployment
                self.update_deployments_table()
                self.update_deployment_details(updated_deployment)
                self.notify(f"Refreshed status for {updated_deployment.deployment_name}")
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

        deployment_id = self.selected_deployment.deployment_id
        deployment_name = self.selected_deployment.deployment_name

        try:
            # Delete the deployment using the SDK
            success = await deployment_sdk.delete(self.ctx, deployment_id)

            if success:
                # Remove from our list
                self.deployments = [
                    d for d in self.deployments if d.deployment_id != deployment_id
                ]
                self.selected_deployment = None
                self.update_deployments_table()
                self.update_status_display()
                self.enable_deployment_actions(False)

                # Clear details table
                details_table = self.query_one("#deployment-details-table", DataTable)
                details_table.clear()

                self.notify(f"Deleted deployment: {deployment_name}")
            else:
                self.notify(f"Failed to delete deployment: {deployment_name}", severity="error")

        except Exception as e:
            logger.error(f"Failed to delete deployment: {e}")
            self.notify(f"Failed to delete deployment: {str(e)}", severity="error")
