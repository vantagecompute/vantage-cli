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
"""Profile Management TabPane for Dashboard

A reusable TabPane widget for managing Vantage profiles in the dashboard.
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
from textual.widgets import Button, DataTable, Input, Label, Static, TabPane, Select
from textual.screen import ModalScreen

from vantage_cli.exceptions import Abort
from vantage_cli.sdk.profile import profile_sdk
from vantage_cli.sdk.profile.schema import Profile
from vantage_cli.utils import get_dev_apps_gh_url


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
                placeholder="Enter profile name (e.g., production, dev)",
                id="profile-name-input"
            )
            
            yield Label("Vantage URL:")
            yield Input(
                placeholder="Enter Vantage API URL",
                value="https://app.vantagecompute.ai",
                id="vantage-url-input"
            )
            
            yield Label("OIDC Max Poll Time (seconds):")
            yield Input(
                placeholder="Default: 300",
                value="300",
                id="oidc-poll-time-input"
            )
            
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
        """
        super().__init__(**kwargs)
        self.profiles = profiles
    
    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="remove-profile-dialog"):
            yield Static("🗑️  Remove Profile", classes="modal-title")
            yield Static("⚠️  Warning: This will permanently delete the profile and its data!", classes="warning-text")
            
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
                yield Button("🗑️  Remove", variant="error", id="remove-btn", disabled=not profile_options)
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

    def __init__(self, ctx: typer.Context, **kwargs: Any) -> None:
        """Initialize the profile management tab pane.

        Args:
            ctx: Typer context with settings and configuration
        """
        super().__init__("👤 Profiles", id="profiles-tab", **kwargs)
        self.ctx = ctx

    def compose(self) -> ComposeResult:
        """Create the profile management layout with split panels."""
        with Vertical():
            yield Static("� Profile Management", classes="section-header")

            # Status and refresh section
            with Horizontal(id="profile-status-bar"):
                yield Static("Status: Ready", id="profile-status")
                yield Static("Last refresh: Never", id="profile-last-refresh-display")
                yield Button("🔄 Refresh", id="refresh-profiles-btn", variant="primary")

            # Main content area - split into left and right panels
            with Horizontal(id="profile-content"):
                # Left panel: Available Profiles
                with Vertical(id="profiles-section"):
                    yield Static("📋 Available Profiles", classes="subsection-header")
                    yield DataTable(id="profiles-table", zebra_stripes=True)

                # Right panel: Profile Details
                with Vertical(id="profile-details-section"):
                    yield Static("📄 Profile Details", classes="subsection-header")
                    yield DataTable(id="profile-details-table", show_header=False)

            # Action buttons
            with Horizontal(id="profile-actions"):
                yield Button("🎯 Activate", id="activate-profile-btn", disabled=True, variant="primary")
                yield Button("📊 View Details", id="view-profile-details-btn", disabled=True)
                yield Button("✏️ Edit", id="edit-profile-btn", disabled=True)
                yield Button("🗑️ Delete", id="delete-profile-btn", disabled=True, variant="error")

    def on_mount(self) -> None:
        """Initialize the profile table when the tab is mounted."""
        logger.info("ProfileManagementTabPane.on_mount() called")
        
        self.setup_profiles_table()
        self.setup_details_table()

        # Debug the context structure
        logger.debug(f"ProfileManagementTabPane context type: {type(self.ctx)}")
        logger.debug(f"ProfileManagementTabPane context: {self.ctx}")

        # Auto-refresh profiles on mount
        self.refresh_profiles()

    def setup_profiles_table(self) -> None:
        """Setup the profiles table with columns."""
        table = self.query_one("#profiles-table", DataTable)
        table.add_columns("Name", "URL", "Active", "API Key Status")
        table.cursor_type = "row"
        table.show_cursor = True
        logger.debug("Profiles table setup complete.")

    def setup_details_table(self) -> None:
        """Setup the profile details table."""
        details_table = self.query_one("#profile-details-table", DataTable)
        details_table.add_columns("Property", "Value")

    @work(exclusive=True)
    async def refresh_profiles(self) -> None:
        """Refresh the profiles list from the local storage."""
        logger.info("refresh_profiles() called")
        self.is_loading = True
        status_widget = self.query_one("#profile-status", Static)
        status_widget.update("Status: Loading profiles...")

        try:
            # Fetch profiles using the SDK
            logger.info("Starting profile refresh...")

            # Get profiles as Profile objects
            profiles_data = await profile_sdk.get_profiles(self.ctx)
            logger.info(f"Fetched {len(profiles_data)} profiles: {[p.name for p in profiles_data]}")

            self.profiles = profiles_data

            # Find the active profile
            self.active_profile = next(
                (profile for profile in profiles_data if profile.is_active), None
            )
            logger.info(f"Active profile: {self.active_profile.name if self.active_profile else 'None'}")

            self.last_refresh = datetime.now()

            # Update the UI
            logger.info("Updating profiles table...")
            self.update_profiles_table()
            logger.info("Updating status display...")
            self.update_status_display()

            logger.info("Profile refresh completed successfully")

        except Abort as e:
            error_msg = f"Failed to fetch profiles: {e.message}"
            logger.error(error_msg)
            status_widget.update(f"Status: Error - {e.message}")
            self.notify(error_msg, severity="error")

        except Exception as e:
            error_msg = f"Unexpected error fetching profiles: {str(e)}"
            logger.error(error_msg)
            logger.exception("Full traceback:")
            status_widget.update(f"Status: Unexpected error - {str(e)}")
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

    def update_status_display(self) -> None:
        """Update the status and last refresh display."""
        status_widget = self.query_one("#profile-status", Static)
        refresh_widget = self.query_one("#profile-last-refresh-display", Static)

        profile_count = len(self.profiles)
        active_profile_name = self.active_profile.name if self.active_profile else "None"
        status_widget.update(
            f"Status: Ready ({profile_count} profiles, active: {active_profile_name})"
        )

        if self.last_refresh:
            refresh_time = self.last_refresh.strftime("%H:%M:%S")
            refresh_widget.update(f"Last refresh: {refresh_time}")

    def update_profile_details(self, profile: Profile) -> None:
        """Update the profile details table with selected profile info."""
        details_table = self.query_one("#profile-details-table", DataTable)
        details_table.clear()

        # Display profile properties using the schema
        details = [
            ("Profile Name", profile.name),
            ("API Base URL", profile.api_base_url),
            ("OIDC Base URL", profile.oidc_base_url),
            ("OIDC Client ID", profile.oidc_client_id),
            ("Is Active", "Yes" if profile.is_active else "No"),
            ("Dev Apps GitHub URL", get_dev_apps_gh_url() or "Not configured"),
        ]

        for key, value in details:
            details_table.add_row(key, str(value))

    def enable_profile_actions(self, enabled: bool) -> None:
        """Enable or disable profile action buttons."""
        activate_btn = self.query_one("#activate-profile-btn", Button)
        view_btn = self.query_one("#view-profile-details-btn", Button)
        edit_btn = self.query_one("#edit-profile-btn", Button)
        delete_btn = self.query_one("#delete-profile-btn", Button)

        activate_btn.disabled = not enabled
        view_btn.disabled = not enabled
        edit_btn.disabled = not enabled
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
            self.create_profile()

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
    async def create_profile(self) -> None:
        """Create a new profile from the form inputs."""
        name_input = self.query_one("#profile-name-input", Input)
        api_key_input = self.query_one("#profile-api-key-input", Input)
        url_input = self.query_one("#profile-url-input", Input)

        name = name_input.value.strip()
        api_key = api_key_input.value.strip()
        url = url_input.value.strip()

        # Validate inputs
        if not name:
            self.notify("Profile name is required", severity="error")
            return
        if not api_key:
            self.notify("API key is required", severity="error")
            return
        if not url:
            self.notify("Vantage URL is required", severity="error")
            return

        try:
            # Create profile data
            profile_data = {"name": name, "api_key": api_key, "vantage_url": url}

            # Create the profile using the SDK
            created_profile = await profile_sdk.create(self.ctx, profile_data)

            if created_profile:
                # Clear form inputs
                name_input.value = ""
                api_key_input.value = ""
                url_input.value = "https://api.vantage.com"

                # Refresh profiles
                self.refresh_profiles()

                self.notify(f"Created profile: {name}", severity="information")
            else:
                self.notify(f"Failed to create profile: {name}", severity="error")

        except Exception as e:
            logger.error(f"Failed to create profile: {e}")
            self.notify(f"Failed to create profile: {str(e)}", severity="error")

    @work(exclusive=True)
    async def activate_profile(self) -> None:
        """Activate the selected profile."""
        if not self.selected_profile:
            return

        profile_name = self.selected_profile.name

        try:
            # Activate the profile using the SDK
            # Note: This would typically involve updating the settings/config
            # For now, we'll simulate this action
            self.notify(f"Activating profile: {profile_name}")

            # In a real implementation, you would call an SDK method like:
            # await profile_sdk.activate(self.ctx, profile_name)

            # For now, just refresh to show the change
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
            success = await profile_sdk.delete(self.ctx, profile_name)

            if success:
                # Remove from our list
                self.profiles = [p for p in self.profiles if p.name != profile_name]
                self.selected_profile = None
                self.update_profiles_table()
                self.update_status_display()
                self.enable_profile_actions(False)

                # Clear details table
                details_table = self.query_one("#profile-details-table", DataTable)
                details_table.clear()

                self.notify(f"Deleted profile: {profile_name}", severity="information")
            else:
                self.notify(f"Failed to delete profile: {profile_name}", severity="error")

        except Exception as e:
            logger.error(f"Failed to delete profile: {e}")
            self.notify(f"Failed to delete profile: {str(e)}", severity="error")
