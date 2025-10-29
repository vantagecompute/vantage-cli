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
"""Credential Management TabPane for Dashboard.

A reusable TabPane widget for managing cloud credentials in the dashboard.
"""

import logging
from datetime import datetime
from typing import List, Optional

import typer
from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label, Select, Static, TabPane

from vantage_cli.sdk.cloud_credential.schema import CloudCredential

logger = logging.getLogger(__name__)


class CreateCredentialModal(ModalScreen[Optional[dict]]):
    """Modal screen for creating a new credential."""

    DEFAULT_CSS = """
    CreateCredentialModal {
        align: center middle;
    }

    #create-credential-dialog {
        width: 80;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #create-credential-dialog .modal-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #create-credential-dialog Label {
        margin-top: 1;
        color: $text;
    }

    #create-credential-dialog Input {
        margin-bottom: 1;
    }

    #create-credential-dialog Select {
        margin-bottom: 1;
    }

    #create-credential-dialog #button-row {
        margin-top: 1;
        height: auto;
        align: center middle;
    }

    #create-credential-dialog Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="create-credential-dialog"):
            yield Static("🔐 Create New Credential", classes="modal-title")

            yield Label("Credential Name:")
            yield Input(
                placeholder="Enter credential name (e.g., my-aws-creds)",
                id="credential-name-input",
            )

            yield Label("Cloud Type:")
            yield Select(
                options=[
                    ("AWS", "aws"),
                    ("GCP", "gcp"),
                    ("Azure", "azure"),
                    ("CUDO Compute", "cudo-compute"),
                    ("On-Premises", "on_prem"),
                    ("Kubernetes", "k8s"),
                ],
                prompt="Select cloud type",
                id="cloud-type-select",
            )

            yield Label("Cloud ID:")
            yield Input(
                placeholder="Enter cloud ID (e.g., aws, cudo-compute)", id="cloud-id-input"
            )

            yield Label("API Key / Access Key:")
            yield Input(
                placeholder="Enter API key or access key", id="api-key-input", password=False
            )

            yield Label("Additional Data (optional):")
            yield Input(
                placeholder="e.g., region:us-west-2 or datacenter:us-dallas-1",
                id="additional-data-input",
            )

            yield Label("Set as Default:")
            yield Select(
                options=[
                    ("No", "false"),
                    ("Yes", "true"),
                ],
                value="false",
                id="default-select",
            )

            with Horizontal(id="button-row"):
                yield Button("✅ Create", variant="success", id="create-btn")
                yield Button("❌ Cancel", variant="error", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses in the modal."""
        if event.button.id == "create-btn":
            # Gather form data
            name_input = self.query_one("#credential-name-input", Input)
            cloud_type_select = self.query_one("#cloud-type-select", Select)
            cloud_id_input = self.query_one("#cloud-id-input", Input)
            api_key_input = self.query_one("#api-key-input", Input)
            additional_data_input = self.query_one("#additional-data-input", Input)
            default_select = self.query_one("#default-select", Select)

            credential_name = name_input.value.strip()
            cloud_id = cloud_id_input.value.strip()
            api_key = api_key_input.value.strip()

            # Validate required fields
            if not credential_name:
                self.notify("Credential name is required", severity="error")
                return

            if not cloud_type_select.value:
                self.notify("Cloud type is required", severity="error")
                return

            if not cloud_id:
                self.notify("Cloud ID is required", severity="error")
                return

            if not api_key:
                self.notify("API key is required", severity="error")
                return

            # Parse additional data
            credentials_data = {"api_key": api_key}
            if additional_data_input.value.strip():
                # Parse key:value format
                for pair in additional_data_input.value.strip().split():
                    if ":" in pair:
                        key, value = pair.split(":", 1)
                        credentials_data[key.strip()] = value.strip()

            # Return the credential data
            credential_data = {
                "name": credential_name,
                "credential_type": str(cloud_type_select.value),
                "cloud_id": cloud_id,
                "credentials_data": credentials_data,
                "default": str(default_select.value) == "true",
            }

            self.dismiss(credential_data)

        elif event.button.id == "cancel-btn":
            self.dismiss(None)


class RemoveCredentialModal(ModalScreen[Optional[str]]):
    """Modal screen for removing a credential."""

    DEFAULT_CSS = """
    RemoveCredentialModal {
        align: center middle;
    }

    #remove-credential-dialog {
        width: 70;
        height: auto;
        border: thick $error;
        background: $surface;
        padding: 1 2;
    }

    #remove-credential-dialog .modal-title {
        text-align: center;
        text-style: bold;
        color: $error;
        margin-bottom: 1;
    }

    #remove-credential-dialog .warning-text {
        text-align: center;
        color: $warning;
        margin-bottom: 1;
    }

    #remove-credential-dialog Label {
        margin-top: 1;
        color: $text;
    }

    #remove-credential-dialog Select {
        margin-bottom: 1;
    }

    #remove-credential-dialog #button-row {
        margin-top: 1;
        height: auto;
        align: center middle;
    }

    #remove-credential-dialog Button {
        margin: 0 1;
    }
    """

    def __init__(self, credentials: List[CloudCredential], **kwargs):
        """Initialize the remove credential modal.

        Args:
            credentials: List of available credentials
            **kwargs: Additional arguments passed to parent widget
        """
        super().__init__(**kwargs)
        self.credentials = credentials

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="remove-credential-dialog"):
            yield Static("🗑️  Remove Credential", classes="modal-title")
            yield Static(
                "⚠️  Warning: This will permanently delete the credential!", classes="warning-text"
            )

            yield Label("Select Credential to Remove:")

            # Create dropdown options from credentials
            credential_options = [
                (f"{cred.name} ({cred.credential_type})", cred.id) for cred in self.credentials
            ]

            if not credential_options:
                yield Static("No credentials available to remove", classes="warning-text")
            else:
                yield Select(
                    options=credential_options,
                    prompt="Select credential to remove",
                    id="credential-select",
                )

            with Horizontal(id="button-row"):
                yield Button(
                    "🗑️  Remove", variant="error", id="remove-btn", disabled=not credential_options
                )
                yield Button("❌ Cancel", variant="primary", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses in the modal."""
        if event.button.id == "remove-btn":
            # Get selected credential
            credential_select = self.query_one("#credential-select", Select)

            if not credential_select.value:
                self.notify("Please select a credential to remove", severity="error")
                return

            # Return the selected credential ID
            credential_id = str(credential_select.value)
            self.dismiss(credential_id)

        elif event.button.id == "cancel-btn":
            self.dismiss(None)


class CredentialManagementTabPane(TabPane):
    """A TabPane widget for credential management functionality."""

    DEFAULT_CSS = """
    CredentialManagementTabPane #credential-filters {
        height: auto;
        padding: 0 1;
        margin: 0;
    }

    CredentialManagementTabPane #credential-main-panel {
        height: 1fr;
        layout: horizontal;
        margin-top: 0;
        padding-top: 0;
    }

    CredentialManagementTabPane #credentials-panel {
        width: 1fr;
        height: 100%;
        padding: 0;
        border: solid $accent;
        border-title-align: center;
        border-title-color: $accent;
        border-title-background: $surface;
        overflow: auto;
    }

    CredentialManagementTabPane #credentials-table {
        height: auto;
    }

    CredentialManagementTabPane #credential-detail-panel {
        width: 1fr;
        height: 100%;
        padding: 0;
        border: solid $accent;
        border-title-align: center;
        border-title-color: $accent;
        border-title-background: $surface;
        overflow: auto;
    }

    CredentialManagementTabPane #credential-detail-scroll {
        height: 100%;
    }

    CredentialManagementTabPane #credential-detail {
        padding: 1;
        height: auto;
    }

    CredentialManagementTabPane #credential-actions {
        height: auto;
        padding: 0 1;
        background: $surface;
    }

    CredentialManagementTabPane Button {
        min-width: 16;
    }
    """

    # Reactive properties for UI updates
    credentials: reactive[List[CloudCredential]] = reactive(list, init=False)
    selected_credential: reactive[Optional[CloudCredential]] = reactive(None, init=False)

    def __init__(
        self,
        title: str,
        ctx: typer.Context,
        credentials: Optional[List[CloudCredential]] = None,
        **kwargs,
    ):
        """Initialize the credential management tab pane.

        Args:
            title: Tab title
            ctx: Typer context
            credentials: Initial list of credentials
            **kwargs: Additional arguments passed to TabPane
        """
        super().__init__(title, **kwargs)
        self.ctx = ctx
        self.credentials = credentials or []
        self.selected_credential = None

    def compose(self) -> ComposeResult:
        """Create the credential management layout with 2-panel horizontal layout."""
        with Vertical():
            yield Static("📜 Cloud Credentials", classes="section-header")

            # Filters and refresh section
            with Horizontal(id="credential-filters"):
                yield Button("🔄 Refresh", id="refresh-credentials-btn", variant="primary")

            # Main 2-panel horizontal layout
            with Horizontal(id="credential-main-panel"):
                # Panel 1: Credentials List
                with Vertical(id="credentials-panel"):
                    # Action buttons for credentials
                    with Horizontal(id="credential-actions"):
                        yield Button("➕ Create", id="create-credential-btn", variant="success")
                        yield Button(
                            "✏️ Update",
                            id="update-credential-btn",
                            variant="primary",
                            disabled=True,
                        )
                        yield Button(
                            "🗑️ Delete", id="delete-credential-btn", variant="error", disabled=True
                        )
                    yield DataTable(id="credentials-table", zebra_stripes=True, cursor_type="row")

                # Panel 2: Credential Detail Viewer
                with Vertical(id="credential-detail-panel"):
                    with ScrollableContainer(id="credential-detail-scroll"):
                        yield Static("Select a credential to view details", id="credential-detail")

    def on_mount(self) -> None:
        """Initialize the credentials table when the widget mounts."""
        # Set border titles for panels
        credentials_panel = self.query_one("#credentials-panel", Vertical)
        credentials_panel.border_title = "Credentials"

        detail_panel = self.query_one("#credential-detail-panel", Vertical)
        detail_panel.border_title = "Credential Details"

        self.setup_credentials_table()
        # Load credentials from SDK on mount
        self.refresh_credentials()

    def setup_credentials_table(self) -> None:
        """Set up the credentials table columns."""
        table = self.query_one("#credentials-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("Name", "Type", "Cloud ID", "Default", "Created")

    def update_credentials_table(self) -> None:
        """Update the credentials table with current data."""
        table = self.query_one("#credentials-table", DataTable)
        table.clear()

        for credential in self.credentials:
            name = credential.name
            cred_type = str(
                credential.credential_type.value
                if hasattr(credential.credential_type, "value")
                else credential.credential_type
            )
            cloud_id = (
                credential.cloud_id[:12] + "..."
                if len(credential.cloud_id) > 12
                else credential.cloud_id
            )
            is_default = "✓" if credential.default else ""
            created = (
                credential.created_at.strftime("%Y-%m-%d")
                if isinstance(credential.created_at, datetime)
                else str(credential.created_at)
            )

            table.add_row(name, cred_type, cloud_id, is_default, created, key=credential.id)

    def update_credential_details(self, credential: CloudCredential) -> None:
        """Update the details viewer with credential information.

        Args:
            credential: The credential to display
        """
        from rich.markup import escape
        from rich.table import Table

        # Create Rich table for details
        details_table = Table(show_header=False, box=None, padding=(0, 1))
        details_table.add_column("Property", style="bold cyan", no_wrap=True)
        details_table.add_column("Value", style="white")

        # Display all credential properties
        details = [
            ("ID", str(credential.id)),
            ("Name", credential.name),
            (
                "Type",
                str(
                    credential.credential_type.value
                    if hasattr(credential.credential_type, "value")
                    else credential.credential_type
                ),
            ),
            ("Cloud ID", credential.cloud_id),
            ("Default", "Yes" if credential.default else "No"),
            (
                "Created",
                credential.created_at.strftime("%Y-%m-%d %H:%M:%S")
                if isinstance(credential.created_at, datetime)
                else str(credential.created_at),
            ),
            (
                "Updated",
                credential.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                if credential.updated_at and isinstance(credential.updated_at, datetime)
                else "N/A",
            ),
        ]

        # Add basic fields
        for key, value in details:
            details_table.add_row(key, escape(str(value)))

        # Add separator
        details_table.add_row("─" * 20, "─" * 50)

        # Display credentials_data fields
        if credential.credentials_data:
            details_table.add_row("[bold]Credentials Data:[/bold]", "")
            for key, value in credential.credentials_data.items():
                # Show full value for all fields (no masking)
                details_table.add_row(f"  {key}", escape(str(value)))
        else:
            details_table.add_row("[bold]Credentials Data:[/bold]", "None")

        # Update the Static widget
        detail_widget = self.query_one("#credential-detail", Static)
        detail_widget.update(details_table)

    def enable_credential_actions(self, enabled: bool) -> None:
        """Enable or disable action buttons.

        Args:
            enabled: Whether to enable the buttons
        """
        update_btn = self.query_one("#update-credential-btn", Button)
        delete_btn = self.query_one("#delete-credential-btn", Button)

        update_btn.disabled = not enabled
        delete_btn.disabled = not enabled

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle credential selection in the table."""
        logger.debug(
            f"Row selected event: table_id={event.data_table.id}, row_key={event.row_key}"
        )

        if event.data_table.id == "credentials-table":
            credential_id = event.row_key
            logger.debug(f"Credential selected: {credential_id}")

            # Find the selected credential
            selected = next((cred for cred in self.credentials if cred.id == credential_id), None)

            if selected:
                logger.debug(f"Found credential data for {credential_id}: {selected}")
                self.selected_credential = selected
                self.update_credential_details(selected)
                self.enable_credential_actions(True)
                self.notify(f"Selected credential: {selected.name}")
            else:
                logger.warning(f"Could not find credential data for {credential_id}")
        else:
            logger.debug(f"Row selection from different table: {event.data_table.id}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "refresh-credentials-btn":
            self.refresh_credentials()

        elif event.button.id == "view-details-btn" and self.selected_credential:
            # Could open a detailed view or modal
            self.notify(f"Viewing details for {self.selected_credential.name}")

        elif event.button.id == "refresh-status-btn" and self.selected_credential:
            # Refresh the specific credential's status
            self.refresh_credential_status()

        elif event.button.id == "manage-credential-btn" and self.selected_credential:
            # Could open credential management actions
            self.notify(f"Managing credential {self.selected_credential.name}")

    @work(exclusive=True)
    async def refresh_credentials(self) -> None:
        """Refresh the credentials list from the SDK."""
        from vantage_cli.sdk.cloud_credential.crud import cloud_credential_sdk

        try:
            # Reload credentials from file
            cloud_credential_sdk._load_from_file()

            # Get all credentials
            self.credentials = cloud_credential_sdk.list()

            self.update_credentials_table()
            self.notify(f"Refreshed {len(self.credentials)} credentials")

        except Exception as e:
            logger.error(f"Failed to refresh credentials: {e}")
            self.notify(f"Failed to refresh credentials: {str(e)}", severity="error")

    @work(exclusive=True)
    async def refresh_credential_status(self) -> None:
        """Refresh the status of the selected credential."""
        if not self.selected_credential:
            return

        credential_id = self.selected_credential.id
        if not credential_id:
            return

        try:
            from vantage_cli.sdk.cloud_credential.crud import cloud_credential_sdk

            # Fetch updated credential details
            updated_credential = cloud_credential_sdk.get(credential_id)

            if updated_credential:
                # Update the credential in our list
                for i, cred in enumerate(self.credentials):
                    if cred.id == credential_id:
                        self.credentials[i] = updated_credential
                        break

                self.selected_credential = updated_credential
                self.update_credentials_table()
                self.update_credential_details(updated_credential)
                self.notify(f"Refreshed status for {updated_credential.name}")
            else:
                self.notify(f"Credential {credential_id} not found", severity="warning")

        except Exception as e:
            logger.error(f"Failed to refresh credential status: {e}")
            self.notify(f"Failed to refresh credential status: {str(e)}", severity="error")


__all__ = [
    "CredentialManagementTabPane",
]
