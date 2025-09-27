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
"""Login Modal for Dashboard Authentication."""

import logging
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, RichLog, Static

logger = logging.getLogger(__name__)


class LoginModal(ModalScreen[Optional[bool]]):
    """Modal screen for displaying login progress and authentication URL."""

    DEFAULT_CSS = """
    LoginModal {
        align: center middle;
    }

    #login-dialog {
        width: 90;
        height: 30;
        border: thick $success;
        background: $surface;
        padding: 1 2;
    }

    #login-dialog .modal-title {
        text-align: center;
        text-style: bold;
        color: $success;
        margin-bottom: 1;
        height: 1;
    }

    #login-dialog #auth-url-box {
        height: 7;
        border: solid $primary;
        background: $panel;
        padding: 1;
        margin: 1 0;
    }

    #login-dialog .url-label {
        text-align: center;
        text-style: bold;
        color: $accent;
        height: 1;
    }

    #login-dialog .url-display {
        text-align: center;
        color: $primary;
        text-style: bold;
        height: 3;
        margin: 1 0;
    }

    #login-dialog .url-instruction {
        text-align: center;
        color: $text-muted;
        text-style: italic;
        height: 1;
    }

    #login-dialog #progress-log {
        height: 12;
        border: solid $accent;
        margin: 1 0;
    }

    #login-dialog #button-row {
        height: 3;
        align: center middle;
    }

    #login-dialog Button {
        margin: 0 1;
    }
    """

    # Reactive properties for updating the modal content
    auth_url: reactive[str] = reactive("")

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="login-dialog"):
            yield Static("🔐 Vantage Authentication", classes="modal-title")

            # URL display box
            with Vertical(id="auth-url-box"):
                yield Static("Authentication URL:", classes="url-label")
                yield Static("", id="url-display", classes="url-display")
                yield Static(
                    "Click 'Copy URL' or open this link in your browser", classes="url-instruction"
                )

            # Progress log
            yield RichLog(id="progress-log", highlight=True, markup=True)

            with Horizontal(id="button-row"):
                yield Button("📋 Copy URL", variant="primary", id="copy-url-btn", disabled=True)
                yield Button("❌ Cancel", variant="error", id="cancel-btn")

    def on_mount(self) -> None:
        """Initialize the modal when mounted."""
        log = self.query_one("#progress-log", RichLog)
        log.write("⏳ Initializing authentication...")

    def add_message(self, message: str) -> None:
        """Add a message to the progress log."""
        try:
            log = self.query_one("#progress-log", RichLog)
            log.write(message)
        except Exception as e:
            logger.error(f"Failed to add message to log: {e}")

    def set_url(self, url: str) -> None:
        """Set the authentication URL and enable copy button."""
        self.auth_url = url
        try:
            url_display = self.query_one("#url-display", Static)
            url_display.update(url)

            # Enable copy button
            copy_btn = self.query_one("#copy-url-btn", Button)
            copy_btn.disabled = False

            self.add_message("🔗 Authentication URL ready")
            self.add_message(f"   {url}")
        except Exception as e:
            logger.error(f"Failed to set URL: {e}")

    def set_complete(self, message: str) -> None:
        """Mark authentication as complete."""
        self.add_message(f"✅ {message}")

        # Schedule dismiss using call_later to avoid event loop conflicts
        def close_modal():
            self.dismiss(True)

        self.call_later(close_modal)

    def set_error(self, message: str) -> None:
        """Mark authentication as failed."""
        self.add_message(f"❌ {message}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-btn":
            self.add_message("❌ Authentication cancelled by user")
            self.dismiss(False)
        elif event.button.id == "copy-url-btn":
            self.copy_url_to_clipboard()

    def copy_url_to_clipboard(self) -> None:
        """Copy the authentication URL to clipboard."""
        if not self.auth_url:
            self.add_message("⚠️  No URL available to copy")
            return

        try:
            # Try multiple clipboard methods
            import shutil
            import subprocess

            # Method 1: Try pyperclip (cross-platform)
            try:
                import pyperclip  # type: ignore[import-untyped]

                pyperclip.copy(self.auth_url)
                self.add_message("✅ URL copied to clipboard!")
                return
            except ImportError:
                pass
            except Exception as e:
                logger.debug(f"pyperclip failed: {e}")

            # Method 2: Try xclip (Linux)
            if shutil.which("xclip"):
                try:
                    subprocess.run(
                        ["xclip", "-selection", "clipboard"],
                        input=self.auth_url.encode(),
                        check=True,
                        capture_output=True,
                    )
                    self.add_message("✅ URL copied to clipboard!")
                    return
                except Exception as e:
                    logger.debug(f"xclip failed: {e}")

            # Method 3: Try xsel (Linux)
            if shutil.which("xsel"):
                try:
                    subprocess.run(
                        ["xsel", "--clipboard", "--input"],
                        input=self.auth_url.encode(),
                        check=True,
                        capture_output=True,
                    )
                    self.add_message("✅ URL copied to clipboard!")
                    return
                except Exception as e:
                    logger.debug(f"xsel failed: {e}")

            # Method 4: Try pbcopy (macOS)
            if shutil.which("pbcopy"):
                try:
                    subprocess.run(
                        ["pbcopy"], input=self.auth_url.encode(), check=True, capture_output=True
                    )
                    self.add_message("✅ URL copied to clipboard!")
                    return
                except Exception as e:
                    logger.debug(f"pbcopy failed: {e}")

            # If we get here, all methods failed
            self.add_message("⚠️  Could not copy to clipboard")
            self.add_message("   Please manually copy the URL above")

        except Exception as e:
            logger.error(f"Failed to copy URL: {e}")
            self.add_message(f"❌ Copy failed: {str(e)}")
