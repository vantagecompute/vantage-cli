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
"""Login Modal for Dashboard Authentication"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.widgets import Button, Static, Label
from textual.screen import ModalScreen
from textual.reactive import reactive


class LoginModal(ModalScreen[Optional[bool]]):
    """Modal screen for displaying login progress and authentication URL."""
    
    DEFAULT_CSS = """
    LoginModal {
        align: center middle;
    }
    
    #login-dialog {
        width: 80;
        height: auto;
        border: thick $success;
        background: $surface;
        padding: 2 3;
    }
    
    #login-dialog .modal-title {
        text-align: center;
        text-style: bold;
        color: $success;
        margin-bottom: 1;
    }
    
    #login-dialog .section-header {
        text-style: bold;
        color: $accent;
        margin-top: 1;
        margin-bottom: 1;
    }
    
    #login-dialog .url-container {
        margin: 1 0;
        padding: 1 2;
        background: $panel;
        border: solid $primary;
    }
    
    #login-dialog .url-header {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    
    #login-dialog .url-text {
        text-align: center;
        color: $primary;
        text-style: bold;
        margin: 1 0;
    }
    
    #login-dialog .url-instruction {
        text-align: center;
        color: $text-muted;
        margin-top: 1;
        text-style: italic;
    }
    
    #login-dialog #copy-url-btn {
        margin-top: 1;
    }
    
    #login-dialog .status-text {
        text-align: center;
        color: $text;
        margin: 1 0;
    }
    
    #login-dialog .spinner-text {
        text-align: center;
        color: $warning;
        margin: 1 0;
        text-style: bold;
    }
    
    #login-dialog .success-text {
        text-align: center;
        color: $success;
        margin: 1 0;
        text-style: bold;
    }
    
    #login-dialog .error-text {
        text-align: center;
        color: $error;
        margin: 1 0;
        text-style: bold;
    }
    
    #login-dialog #button-row {
        margin-top: 2;
        height: auto;
        align: center middle;
    }
    
    #login-dialog Button {
        margin: 0 1;
    }
    """
    
    # Reactive properties for updating the modal content
    status_message: reactive[str] = reactive("Initializing authentication...")
    auth_url: reactive[str] = reactive("")
    show_url: reactive[bool] = reactive(False)
    is_complete: reactive[bool] = reactive(False)
    is_error: reactive[bool] = reactive(False)
    
    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="login-dialog"):
            yield Static("🔐 Vantage Authentication", classes="modal-title")
            
            yield Static("", id="status-message", classes="status-text")
            
            # URL section (shown when available)
            yield Vertical(id="auth-url-container")
            
            with Horizontal(id="button-row"):
                yield Button("📋 Copy URL", variant="primary", id="copy-url-btn", disabled=True)
                yield Button("❌ Cancel", variant="error", id="cancel-btn")
    
    def on_mount(self) -> None:
        """Called when the modal is mounted."""
        self.update_display()
    
    def watch_status_message(self, new_message: str) -> None:
        """Update status message when it changes."""
        self.update_display()
    
    def watch_show_url(self, show: bool) -> None:
        """Update URL visibility when it changes."""
        self.update_display()
    
    def watch_is_complete(self, complete: bool) -> None:
        """Handle completion state."""
        if complete:
            # Auto-dismiss after a short delay
            self.set_timer(1.5, lambda: self.dismiss(True))
    
    def update_display(self) -> None:
        """Update the modal display based on current state."""
        try:
            # Update status message
            status_widget = self.query_one("#status-message", Static)
            if self.is_error:
                status_widget.update(f"❌ {self.status_message}")
                status_widget.add_class("error-text")
                status_widget.remove_class("status-text")
                status_widget.remove_class("spinner-text")
                status_widget.remove_class("success-text")
            elif self.is_complete:
                status_widget.update(f"✅ {self.status_message}")
                status_widget.add_class("success-text")
                status_widget.remove_class("status-text")
                status_widget.remove_class("spinner-text")
                status_widget.remove_class("error-text")
            else:
                status_widget.update(f"⏳ {self.status_message}")
                status_widget.add_class("spinner-text")
                status_widget.remove_class("status-text")
                status_widget.remove_class("success-text")
                status_widget.remove_class("error-text")
            
            # Update URL section
            url_container = self.query_one("#auth-url-container", Vertical)
            copy_btn = self.query_one("#copy-url-btn", Button)
            
            # Clear existing content
            url_container.remove_children()
            
            if self.show_url and self.auth_url:
                # Show URL with better formatting
                url_container.mount(
                    Static("🔗 Authentication URL", classes="url-header")
                )
                url_container.mount(
                    Static(self.auth_url, classes="url-text")
                )
                url_container.mount(
                    Static(
                        "Click the URL above to copy it, then paste in your browser",
                        classes="url-instruction"
                    )
                )
                url_container.add_class("url-container")
                
                # Enable copy button
                copy_btn.disabled = False
            else:
                url_container.remove_class("url-container")
                # Disable copy button
                copy_btn.disabled = True
                
        except Exception as e:
            logger.debug(f"Error updating login modal display: {e}")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses in the modal."""
        if event.button.id == "cancel-btn":
            self.dismiss(False)
        elif event.button.id == "copy-url-btn":
            if self.auth_url:
                # Copy URL to clipboard
                self.copy_url_to_clipboard()
    
    def copy_url_to_clipboard(self) -> None:
        """Copy the authentication URL to the system clipboard."""
        try:
            # Try using pyperclip if available
            try:
                import pyperclip
                pyperclip.copy(self.auth_url)
                self.notify("✅ URL copied to clipboard!", severity="information", timeout=3)
                return
            except ImportError:
                pass
            
            # Fallback: Try using subprocess with common clipboard commands
            import subprocess
            import platform
            
            system = platform.system()
            
            if system == "Darwin":  # macOS
                subprocess.run(['pbcopy'], input=self.auth_url.encode(), check=True)
                self.notify("✅ URL copied to clipboard!", severity="information", timeout=3)
            elif system == "Linux":
                # Try xclip first
                try:
                    subprocess.run(['xclip', '-selection', 'clipboard'], 
                                 input=self.auth_url.encode(), check=True)
                    self.notify("✅ URL copied to clipboard!", severity="information", timeout=3)
                except FileNotFoundError:
                    # Try xsel as fallback
                    try:
                        subprocess.run(['xsel', '--clipboard', '--input'], 
                                     input=self.auth_url.encode(), check=True)
                        self.notify("✅ URL copied to clipboard!", severity="information", timeout=3)
                    except FileNotFoundError:
                        # No clipboard tool available
                        self.notify(
                            "⚠️ Could not copy to clipboard. Please install xclip or xsel.",
                            severity="warning",
                            timeout=5
                        )
            elif system == "Windows":
                subprocess.run(['clip'], input=self.auth_url.encode(), check=True)
                self.notify("✅ URL copied to clipboard!", severity="information", timeout=3)
            else:
                self.notify("⚠️ Clipboard not supported on this system", severity="warning", timeout=5)
                
        except Exception as e:
            logger.debug(f"Error copying URL to clipboard: {e}")
            self.notify(
                f"⚠️ Failed to copy URL: {str(e)}",
                severity="warning",
                timeout=5
            )
    
    def set_status(self, message: str, show_url: bool = False, url: str = "", 
                   is_complete: bool = False, is_error: bool = False) -> None:
        """Update the modal status.
        
        Args:
            message: Status message to display
            show_url: Whether to show the authentication URL
            url: The authentication URL
            is_complete: Whether authentication is complete
            is_error: Whether there was an error
        """
        self.status_message = message
        self.show_url = show_url
        self.auth_url = url
        self.is_complete = is_complete
        self.is_error = is_error
