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
"""Profile Management TabPane for Dashboard.

A reusable TabPane widget for managing Vantage profiles in the dashboard.
"""

import logging
from datetime import datetime
from typing import Any, List, Optional

import typer
from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label, Select, Static, TabPane

from vantage_cli.exceptions import Abort
from vantage_cli.sdk.profile import profile_sdk
from vantage_cli.sdk.profile.schema import Profile

logger = logging.getLogger(__name__)


class CreateProfileModal(ModalScreen[Optional[dict]]):
    """Modal screen for creating a new profile."""

    DEFAULT_CSS = """
    CreateProfileModal {
        align: center middle;
    }

    #create-profile-dialog {
        width: 80;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #create-profile-dialog .modal-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #create-profile-dialog Label {
        margin-top: 1;
        color: $text;
    }

    #create-profile-dialog Input {
        margin-bottom: 1;
    }

    #create-profile-dialog Select {
        margin-bottom: 1;
    }

    #create-profile-dialog #button-row {
        margin-top: 1;
        height: auto;
        align: center middle;
    }

    #create-profile-dialog Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="create-profile-dialog"):
            yield Static("👤 Create New Profile", classes="modal-title")

            yield Label("Profile Name:")
            yield Input(
                placeholder="Enter profile name (e.g., production, dev)", id="profile-name-input"
            )

            yield Label("Vantage URL:")
            yield Input(
                placeholder="Enter Vantage API URL",
                value="https://app.vantagecompute.ai",
                id="vantage-url-input",
            )

            yield Label("OIDC Max Poll Time (seconds):")
            yield Input(placeholder="Default: 300", value="300", id="oidc-poll-time-input")

            yield Label("Activate Profile:")
            yield Select(
                options=[
                    ("No", "false"),
                    ("Yes", "true"),
                ],
                value="false",
                id="activate-select",
            )

            with Horizontal(id="button-row"):
                yield Button("✅ Create", variant="success", id="create-btn")
                yield Button("❌ Cancel", variant="error", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses in the modal."""
        if event.button.id == "create-btn":
            # Gather form data
            name_input = self.query_one("#profile-name-input", Input)
            url_input = self.query_one("#vantage-url-input", Input)
            poll_time_input = self.query_one("#oidc-poll-time-input", Input)
            activate_select = self.query_one("#activate-select", Select)

            profile_name = name_input.value.strip()
            vantage_url = url_input.value.strip()
            poll_time_str = poll_time_input.value.strip()

            # Validate required fields
            if not profile_name:
                self.notify("Profile name is required", severity="error")
                return

            if not vantage_url:
                self.notify("Vantage URL is required", severity="error")
                return

            # Parse poll time
            try:
                poll_time = int(poll_time_str) if poll_time_str else 300
            except ValueError:
                self.notify("OIDC poll time must be a number", severity="error")
                return

            # Return the profile data
            profile_data = {
                "name": profile_name,
                "settings": {
                    "vantage_url": vantage_url,
                    "oidc_max_poll_time": poll_time,
                },
                "activate": str(activate_select.value) == "true",
            }

            self.dismiss(profile_data)

        elif event.button.id == "cancel-btn":
            self.dismiss(None)


class RemoveProfileModal(ModalScreen[Optional[str]]):
    """Modal screen for removing a profile."""

    DEFAULT_CSS = """
    RemoveProfileModal {
        align: center middle;
    }

    #remove-profile-dialog {
        width: 70;
        height: auto;
        border: thick $error;
        background: $surface;
        padding: 1 2;
    }

    #remove-profile-dialog .modal-title {
        text-align: center;
        text-style: bold;
        color: $error;
        margin-bottom: 1;
    }

    #remove-profile-dialog .warning-text {
        text-align: center;
        color: $warning;
        margin-bottom: 1;
    }

    #remove-profile-dialog Label {
        margin-top: 1;
        color: $text;
    }

    #remove-profile-dialog Select {
        margin-bottom: 1;
    }

    #remove-profile-dialog #button-row {
        margin-top: 1;
        height: auto;
        align: center middle;
    }

    #remove-profile-dialog Button {
        margin: 0 1;
    }
    """

    def __init__(self, profiles: List[Profile], **kwargs):
        """Initialize the remove profile modal.

        Args:
            profiles: List of available profiles
            **kwargs: Additional arguments passed to parent widget
        """
        super().__init__(**kwargs)
        self.profiles = profiles

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="remove-profile-dialog"):
            yield Static("🗑️  Remove Profile", classes="modal-title")
            yield Static(
                "⚠️  Warning: This will permanently delete the profile and its data!",
                classes="warning-text",
            )

            yield Label("Select Profile to Remove:")

            # Create dropdown options from profiles
            profile_options = [
                (f"{prof.name}{'  (active)' if prof.is_active else ''}", prof.name)
                for prof in self.profiles
            ]

            if not profile_options:
                yield Static("No profiles available to remove", classes="warning-text")
            else:
                yield Select(
                    options=profile_options,
                    prompt="Select profile to remove",
                    id="profile-select",
                )

            with Horizontal(id="button-row"):
                yield Button(
                    "🗑️  Remove", variant="error", id="remove-btn", disabled=not profile_options
                )
                yield Button("❌ Cancel", variant="primary", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses in the modal."""
        if event.button.id == "remove-btn":
            # Get selected profile
            profile_select = self.query_one("#profile-select", Select)

            if not profile_select.value:
                self.notify("Please select a profile to remove", severity="error")
                return

            # Return the selected profile name
            profile_name = str(profile_select.value)
            self.dismiss(profile_name)

        elif event.button.id == "cancel-btn":
            self.dismiss(None)


class ProfileManagementTabPane(TabPane):
    """A TabPane widget for profile management functionality."""

    # Reactive attributes for profile data
    profiles: reactive[List[Profile]] = reactive([])
    selected_profile: reactive[Optional[Profile]] = reactive(None)
    active_profile: reactive[Optional[Profile]] = reactive(None)
    is_loading: reactive[bool] = reactive(False)
    last_refresh: reactive[Optional[datetime]] = reactive(None)

    DEFAULT_CSS = """
    ProfileManagementTabPane #profile-filters {
        height: auto;
        padding: 0 1;
        margin: 0;
    }

    ProfileManagementTabPane #profile-main-panel {
        height: 1fr;
        layout: horizontal;
        margin-top: 0;
        padding-top: 0;
    }

    ProfileManagementTabPane #profiles-panel {
        width: 1fr;
        height: 100%;
        padding: 0;
        border: solid $accent;
        border-title-align: center;
        border-title-color: $accent;
        border-title-background: $surface;
        overflow: auto;
    }

    ProfileManagementTabPane #profile-detail-panel {
        width: 1fr;
        height: 100%;
        padding: 0;
        border: solid $accent;
        border-title-align: center;
        border-title-color: $accent;
        border-title-background: $surface;
        overflow: auto;
    }

    ProfileManagementTabPane #profiles-table {
        height: auto;
    }

    ProfileManagementTabPane #profile-detail-scroll {
        height: 100%;
    }

    ProfileManagementTabPane #profile-detail {
        padding: 1;
        height: auto;
    }

    ProfileManagementTabPane #profile-actions {
        height: auto;
        padding: 0 1;
        background: $surface;
    }

    ProfileManagementTabPane Button {
        min-width: 16;
    }
    """

    def __init__(self, ctx: typer.Context, **kwargs: Any) -> None:
        """Initialize the profile management tab pane.

        Args:
            ctx: Typer context with settings and configuration
            **kwargs: Additional arguments passed to parent widget
        """
        super().__init__("👤 Profiles", id="profiles-tab", **kwargs)
        self.ctx = ctx

    def compose(self) -> ComposeResult:
        """Create the profile management layout with 2-panel horizontal layout."""
        with Vertical():
            yield Static("👤 Profile Management", classes="section-header")

            # Filters and refresh section
            with Horizontal(id="profile-filters"):
                yield Button("🔄 Refresh", id="refresh-profiles-btn", variant="primary")

            # Main 2-panel horizontal layout
            with Horizontal(id="profile-main-panel"):
                # Panel 1: Profiles List
                with Vertical(id="profiles-panel"):
                    # Action buttons for profiles
                    with Horizontal(id="profile-actions"):
                        yield Button("➕ Create", id="create-profile-btn", variant="success")
                        yield Button(
                            "🎯 Activate",
                            id="activate-profile-btn",
                            variant="primary",
                            disabled=True,
                        )
                        yield Button(
                            "🗑️ Delete", id="delete-profile-btn", variant="error", disabled=True
                        )
                    yield DataTable(id="profiles-table", zebra_stripes=True, cursor_type="row")

                # Panel 2: Profile Detail Viewer
                with Vertical(id="profile-detail-panel"):
                    with ScrollableContainer(id="profile-detail-scroll"):
                        yield Static("Select a profile to view details", id="profile-detail")

    def on_mount(self) -> None:
        """Initialize the profile table when the tab is mounted."""
        logger.info("ProfileManagementTabPane.on_mount() called")

        # Set border titles for panels
        profiles_panel = self.query_one("#profiles-panel", Vertical)
        profiles_panel.border_title = "Profiles"

        detail_panel = self.query_one("#profile-detail-panel", Vertical)
        detail_panel.border_title = "Profile Details"

        self.setup_profiles_table()

        # Debug the context structure
        logger.debug(f"ProfileManagementTabPane context type: {type(self.ctx)}")
        logger.debug(f"ProfileManagementTabPane context: {self.ctx}")

        # Auto-refresh profiles on mount
        self.refresh_profiles()

    def setup_profiles_table(self) -> None:
        """Set up the profiles table with columns."""
        table = self.query_one("#profiles-table", DataTable)
        table.add_columns("Name", "URL", "Active", "API Key Status")
        table.cursor_type = "row"
        table.show_cursor = True
        logger.debug("Profiles table setup complete.")

    @work(exclusive=True)
    async def refresh_profiles(self) -> None:
        """Refresh the profiles list from the local storage."""
        logger.info("refresh_profiles() called")
        self.is_loading = True

        try:
            # Fetch profiles using the SDK
            logger.info("Starting profile refresh...")

            # Get profiles as Profile objects
            profiles_data = profile_sdk.list()
            logger.info(
                f"Fetched {len(profiles_data)} profiles: {[p.name for p in profiles_data]}"
            )

            self.profiles = profiles_data

            # Find the active profile
            self.active_profile = next(
                (profile for profile in profiles_data if profile.is_active), None
            )
            logger.info(
                f"Active profile: {self.active_profile.name if self.active_profile else 'None'}"
            )

            self.last_refresh = datetime.now()

            # Update the UI
            logger.info("Updating profiles table...")
            self.update_profiles_table()

            logger.info("Profile refresh completed successfully")
            self.notify(f"Loaded {len(self.profiles)} profiles", severity="information")

        except Abort as e:
            error_msg = f"Failed to fetch profiles: {e.message}"
            logger.error(error_msg)
            self.notify(error_msg, severity="error")

        except Exception as e:
            error_msg = f"Unexpected error fetching profiles: {str(e)}"
            logger.error(error_msg)
            logger.exception("Full traceback:")
            self.notify(error_msg, severity="error")

        finally:
            self.is_loading = False
            logger.info(f"is_loading set to False, profiles count: {len(self.profiles)}")

    def update_profiles_table(self) -> None:
        """Update the profiles table with current data."""
        table = self.query_one("#profiles-table", DataTable)
        table.clear()

        logger.debug(f"Updating profiles table with {len(self.profiles)} profiles")

        if not self.profiles:
            logger.debug("No profiles to display")
            return

        for i, profile in enumerate(self.profiles):
            logger.debug(f"Processing profile {i}: {profile.name}")

            # Use the Profile schema object properties
            name = profile.name
            url = profile.api_base_url  # Using computed field
            is_active = "✅ Active" if profile.is_active else "⚪ Inactive"
            api_key_status = "🔑 Connected" if profile.settings else "❌ Not configured"

            logger.debug(f"Adding row: {name}, {url}, {is_active}, {api_key_status}")
            table.add_row(name, url, is_active, api_key_status, key=profile.name)

    def update_profile_details(self, profile: Profile) -> None:
        """Update the profile details viewer with selected profile info."""
        from rich.markup import escape
        from rich.table import Table

        # Create Rich table for details
        details_table = Table(show_header=False, box=None, padding=(0, 1))
        details_table.add_column("Property", style="bold cyan", no_wrap=True)
        details_table.add_column("Value", style="white")

        # Profile Core Properties
        details_table.add_row("", "")  # Spacer
        details_table.add_row("[bold yellow]PROFILE INFORMATION[/bold yellow]", "")
        details_table.add_row("Profile Name", escape(profile.name))
        details_table.add_row("Is Active", "✅ Yes" if profile.is_active else "⚪ No")

        # Profile Computed Fields (URLs)
        details_table.add_row("", "")  # Spacer
        details_table.add_row("[bold yellow]COMPUTED URLS[/bold yellow]", "")
        details_table.add_row("API Base URL", escape(profile.api_base_url))
        details_table.add_row("Tunnel URL", escape(profile.tunnel_url))
        details_table.add_row("LDAP URL", escape(profile.ldap_url))
        details_table.add_row("OIDC Base URL", escape(profile.oidc_base_url))
        details_table.add_row("OIDC Client ID", escape(profile.oidc_client_id))

        # Settings Properties
        details_table.add_row("", "")  # Spacer
        details_table.add_row("[bold yellow]SETTINGS[/bold yellow]", "")
        details_table.add_row("Vantage URL", escape(profile.settings.vantage_url))
        details_table.add_row("OIDC Domain", escape(profile.settings.oidc_domain))
        details_table.add_row(
            "OIDC Max Poll Time", f"{profile.settings.oidc_max_poll_time} seconds"
        )
        details_table.add_row("OIDC Token URL", escape(profile.settings.oidc_token_url))

        # Cloud Credentials
        if profile.cloud_credentials:
            details_table.add_row("", "")  # Spacer
            details_table.add_row("[bold yellow]CLOUD CREDENTIALS[/bold yellow]", "")
            for i, cred in enumerate(profile.cloud_credentials, 1):
                details_table.add_row(
                    f"Credential {i}", escape(cred.name if hasattr(cred, "name") else str(cred))
                )
        else:
            details_table.add_row("", "")  # Spacer
            details_table.add_row("Cloud Credentials", "[dim]None configured[/dim]")

        # Update the Static widget
        detail_widget = self.query_one("#profile-detail", Static)
        detail_widget.update(details_table)

    def enable_profile_actions(self, enabled: bool) -> None:
        """Enable or disable profile action buttons."""
        activate_btn = self.query_one("#activate-profile-btn", Button)
        delete_btn = self.query_one("#delete-profile-btn", Button)

        activate_btn.disabled = not enabled
        delete_btn.disabled = not enabled

        # Disable activate button if this profile is already active
        if enabled and self.selected_profile and self.selected_profile.is_active:
            activate_btn.disabled = True

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle profile selection in the table."""
        logger.debug(
            f"Row selected event: table_id={event.data_table.id}, row_key={event.row_key}"
        )

        if event.data_table.id == "profiles-table":
            profile_name = event.row_key
            logger.debug(f"Profile selected: {profile_name}")

            # Find the selected profile
            selected = next(
                (profile for profile in self.profiles if profile.name == profile_name), None
            )

            if selected:
                logger.debug(f"Found profile data for {profile_name}: {selected}")
                self.selected_profile = selected
                self.update_profile_details(selected)
                self.enable_profile_actions(True)
                self.notify(f"Selected profile: {selected.name}")
            else:
                logger.warning(f"Could not find profile data for {profile_name}")
        else:
            logger.debug(f"Row selection from different table: {event.data_table.id}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "refresh-profiles-btn":
            self.refresh_profiles()

        elif event.button.id == "create-profile-btn":
            # Delegate to the dashboard's modal handler
            # The dashboard already has open_create_profile_modal() which uses ProfileSDK
            self.notify(
                "Profile creation should be handled by dashboard modal", severity="information"
            )

        elif event.button.id == "activate-profile-btn" and self.selected_profile:
            self.activate_profile()

        elif event.button.id == "view-profile-details-btn" and self.selected_profile:
            self.notify(f"Viewing details for {self.selected_profile.name}")

        elif event.button.id == "edit-profile-btn" and self.selected_profile:
            self.notify(
                f"Editing profile {self.selected_profile.name} - Not implemented yet",
                severity="warning",
            )

        elif event.button.id == "delete-profile-btn" and self.selected_profile:
            self.delete_profile()

    @work(exclusive=True)
    async def activate_profile(self) -> None:
        """Activate the selected profile."""
        if not self.selected_profile:
            return

        profile_name = self.selected_profile.name

        try:
            # Actually activate the profile using the SDK
            self.notify(f"Activating profile: {profile_name}")
            profile_sdk.activate(profile_name)
            self.refresh_profiles()
            self.notify(f"Activated profile: {profile_name}", severity="information")
        except Exception as e:
            logger.error(f"Failed to activate profile: {e}")
            self.notify(f"Failed to activate profile: {str(e)}", severity="error")

    @work(exclusive=True)
    async def delete_profile(self) -> None:
        """Delete the selected profile."""
        if not self.selected_profile:
            return

        profile_name = self.selected_profile.name

        # Prevent deleting the active profile
        if self.selected_profile.is_active:
            self.notify("Cannot delete the active profile", severity="warning")
            return

        try:
            # Delete the profile using the SDK
            success = profile_sdk.delete(profile_name)

            if success:
                # Remove from our list
                self.profiles = [p for p in self.profiles if p.name != profile_name]
                self.selected_profile = None
                self.update_profiles_table()
                self.enable_profile_actions(False)

                # Clear details viewer
                detail_widget = self.query_one("#profile-detail", Static)
                detail_widget.update("Select a profile to view details")

                self.notify(f"Deleted profile: {profile_name}", severity="information")
            else:
                self.notify(f"Failed to delete profile: {profile_name}", severity="error")

        except Exception as e:
            logger.error(f"Failed to delete profile: {e}")
            self.notify(f"Failed to delete profile: {str(e)}", severity="error")
