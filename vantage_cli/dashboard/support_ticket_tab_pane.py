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
"""Support Ticket Management TabPane for Dashboard.

A reusable TabPane widget for managing Vantage support tickets in the dashboard.
"""

import logging
from typing import List, Optional

import typer
from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label, Select, Static, TabPane, TextArea

from vantage_cli.sdk.support_ticket.crud import SupportTicketSDK
from vantage_cli.sdk.support_ticket.schema import (
    Comment,
    SeverityLevel,
    SupportTicket,
    TicketStatus,
)

logger = logging.getLogger(__name__)


class CreateSupportTicketModal(ModalScreen[Optional[dict]]):
    """Modal screen for creating a new support ticket."""

    DEFAULT_CSS = """
    CreateSupportTicketModal {
        align: center middle;
    }

    #create-ticket-dialog {
        width: 80;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #create-ticket-dialog .modal-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #create-ticket-dialog Label {
        margin-top: 1;
        color: $text;
    }

    #create-ticket-dialog Input {
        margin-bottom: 1;
    }

    #create-ticket-dialog TextArea {
        height: 8;
        margin-bottom: 1;
    }

    #create-ticket-dialog Select {
        margin-bottom: 1;
    }

    #create-ticket-dialog #button-row {
        margin-top: 1;
        height: auto;
        align: center middle;
    }

    #create-ticket-dialog Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="create-ticket-dialog"):
            yield Static("🎫 Create New Support Ticket", classes="modal-title")

            yield Label("Title:")
            yield Input(placeholder="Enter ticket title", id="ticket-title-input")

            yield Label("Description:")
            yield TextArea(text="", id="ticket-description-input")

            yield Label("Priority:")
            yield Select(
                options=[
                    ("Low", SeverityLevel.LOW.value),
                    ("Medium", SeverityLevel.MEDIUM.value),
                    ("High", SeverityLevel.HIGH.value),
                    ("Critical", SeverityLevel.CRITICAL.value),
                ],
                value=SeverityLevel.MEDIUM.value,
                id="priority-select",
            )

            with Horizontal(id="button-row"):
                yield Button("✅ Create", variant="success", id="create-btn")
                yield Button("❌ Cancel", variant="error", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses in the modal."""
        if event.button.id == "create-btn":
            # Gather form data
            title_input = self.query_one("#ticket-title-input", Input)
            description_input = self.query_one("#ticket-description-input", TextArea)
            priority_select = self.query_one("#priority-select", Select)

            title = title_input.value.strip()
            description = description_input.text.strip()
            priority = str(priority_select.value)

            # Validate required fields
            if not title:
                self.notify("Title is required", severity="error")
                return

            if not description:
                self.notify("Description is required", severity="error")
                return

            # Return the data
            self.dismiss(
                {
                    "title": title,
                    "description": description,
                    "priority": priority,
                }
            )
        elif event.button.id == "cancel-btn":
            self.dismiss(None)


class UpdateSupportTicketModal(ModalScreen[Optional[dict]]):
    """Modal screen for updating an existing support ticket."""

    def __init__(self, ticket: SupportTicket, **kwargs):
        super().__init__(**kwargs)
        self.ticket = ticket

    DEFAULT_CSS = """
    UpdateSupportTicketModal {
        align: center middle;
    }

    #update-ticket-dialog {
        width: 80;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #update-ticket-dialog .modal-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #update-ticket-dialog Label {
        margin-top: 1;
        color: $text;
    }

    #update-ticket-dialog Input {
        margin-bottom: 1;
    }

    #update-ticket-dialog TextArea {
        height: 8;
        margin-bottom: 1;
    }

    #update-ticket-dialog Select {
        margin-bottom: 1;
    }

    #update-ticket-dialog #button-row {
        margin-top: 1;
        height: auto;
        align: center middle;
    }

    #update-ticket-dialog Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="update-ticket-dialog"):
            yield Static("✏️ Update Support Ticket", classes="modal-title")

            yield Label("Title:")
            yield Input(
                value=self.ticket.title, placeholder="Enter ticket title", id="ticket-title-input"
            )

            yield Label("Description:")
            yield TextArea(text=self.ticket.description or "", id="ticket-description-input")

            yield Label("Status:")
            yield Select(
                options=[
                    ("Open", TicketStatus.OPEN.value),
                    ("In Progress", TicketStatus.IN_PROGRESS.value),
                    ("Closed", TicketStatus.CLOSED.value),
                ],
                value=self.ticket.status.value,
                id="status-select",
            )

            yield Label("Priority:")
            yield Select(
                options=[
                    ("Low", SeverityLevel.LOW.value),
                    ("Medium", SeverityLevel.MEDIUM.value),
                    ("High", SeverityLevel.HIGH.value),
                    ("Critical", SeverityLevel.CRITICAL.value),
                ],
                value=self.ticket.priority.value,
                id="priority-select",
            )

            with Horizontal(id="button-row"):
                yield Button("✅ Update", variant="success", id="update-btn")
                yield Button("❌ Cancel", variant="error", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses in the modal."""
        if event.button.id == "update-btn":
            # Gather form data
            title_input = self.query_one("#ticket-title-input", Input)
            description_input = self.query_one("#ticket-description-input", TextArea)
            status_select = self.query_one("#status-select", Select)
            priority_select = self.query_one("#priority-select", Select)

            title = title_input.value.strip()
            description = description_input.text.strip()
            status = str(status_select.value)
            priority = str(priority_select.value)

            # Validate required fields
            if not title:
                self.notify("Title is required", severity="error")
                return

            # Return the data including the ticket ID
            self.dismiss(
                {
                    "ticket_id": self.ticket.id,
                    "title": title,
                    "description": description,
                    "status": status,
                    "priority": priority,
                }
            )
        elif event.button.id == "cancel-btn":
            self.dismiss(None)


class CreateCommentModal(ModalScreen[Optional[dict]]):
    """Modal screen for creating a new comment on a support ticket."""

    DEFAULT_CSS = """
    CreateCommentModal {
        align: center middle;
    }

    #create-comment-dialog {
        width: 70;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #create-comment-dialog .modal-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #create-comment-dialog Label {
        margin-top: 1;
        color: $text;
    }

    #create-comment-dialog TextArea {
        height: 10;
        margin-bottom: 1;
    }

    #create-comment-dialog #button-row {
        margin-top: 1;
        height: auto;
        align: center middle;
    }

    #create-comment-dialog Button {
        margin: 0 1;
    }
    """

    def __init__(self, ticket_id: str, **kwargs):
        """Initialize the create comment modal.

        Args:
            ticket_id: ID of the ticket to add comment to
            **kwargs: Additional arguments passed to parent widget
        """
        super().__init__(**kwargs)
        self.ticket_id = ticket_id

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="create-comment-dialog"):
            yield Static(f"💬 Add Comment to Ticket {self.ticket_id[:8]}", classes="modal-title")

            yield Label("Comment:")
            yield TextArea(text="", id="comment-text-input")

            with Horizontal(id="button-row"):
                yield Button("✅ Add Comment", variant="success", id="create-btn")
                yield Button("❌ Cancel", variant="error", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses in the modal."""
        if event.button.id == "create-btn":
            # Gather form data
            comment_input = self.query_one("#comment-text-input", TextArea)
            comment_text = comment_input.text.strip()

            # Validate required fields
            if not comment_text:
                self.notify("Comment text is required", severity="error")
                return

            # Return the data
            self.dismiss(
                {
                    "ticket_id": self.ticket_id,
                    "comment_text": comment_text,
                }
            )
        elif event.button.id == "cancel-btn":
            self.dismiss(None)


class UpdateCommentModal(ModalScreen[Optional[dict]]):
    """Modal screen for updating an existing comment."""

    DEFAULT_CSS = """
    UpdateCommentModal {
        align: center middle;
    }

    #update-comment-dialog {
        width: 70;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #update-comment-dialog .modal-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #update-comment-dialog Label {
        margin-top: 1;
        color: $text;
    }

    #update-comment-dialog TextArea {
        height: 10;
        margin-bottom: 1;
    }

    #update-comment-dialog #button-row {
        margin-top: 1;
        height: auto;
        align: center middle;
    }

    #update-comment-dialog Button {
        margin: 0 1;
    }
    """

    def __init__(self, comment: Comment, **kwargs):
        """Initialize the update comment modal.

        Args:
            comment: Comment object to update
            **kwargs: Additional arguments passed to parent widget
        """
        super().__init__(**kwargs)
        self.comment = comment

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="update-comment-dialog"):
            yield Static("✏️ Update Comment", classes="modal-title")

            yield Label("Comment:")
            yield TextArea(text=self.comment.raw_text or "", id="comment-text-input")

            with Horizontal(id="button-row"):
                yield Button("✅ Update", variant="success", id="update-btn")
                yield Button("❌ Cancel", variant="error", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses in the modal."""
        if event.button.id == "update-btn":
            # Gather form data
            comment_input = self.query_one("#comment-text-input", TextArea)
            comment_text = comment_input.text.strip()

            # Validate required fields
            if not comment_text:
                self.notify("Comment text is required", severity="error")
                return

            # Return the data including the comment ID
            self.dismiss(
                {
                    "comment_id": self.comment.id,
                    "comment_text": comment_text,
                }
            )
        elif event.button.id == "cancel-btn":
            self.dismiss(None)


class SupportTicketManagementTabPane(TabPane):
    """TabPane for managing support tickets with 3-panel horizontal layout."""

    DEFAULT_CSS = """
    SupportTicketManagementTabPane #support-ticket-filters {
        height: auto;
        padding: 0 1;
        margin: 0;
    }

    SupportTicketManagementTabPane #support-ticket-main-panel {
        height: 1fr;
        layout: horizontal;
        margin-top: 0;
        padding-top: 0;
    }

    SupportTicketManagementTabPane #tickets-panel {
        width: 1fr;
        height: 100%;
        padding: 0;
        border: solid $accent;
        border-title-align: center;
        border-title-color: $accent;
        border-title-background: $surface;
        overflow: auto;
    }

    SupportTicketManagementTabPane #comments-list-panel {
        width: 1fr;
        height: 100%;
        padding: 0;
        border: solid $accent;
        border-title-align: center;
        border-title-color: $accent;
        border-title-background: $surface;
        overflow: auto;
    }

    SupportTicketManagementTabPane #comment-detail-panel {
        width: 1fr;
        height: 100%;
        padding: 0;
        border: solid $accent;
        border-title-align: center;
        border-title-color: $accent;
        border-title-background: $surface;
        overflow: auto;
    }

    SupportTicketManagementTabPane #support-tickets-table {
        height: auto;
    }

    SupportTicketManagementTabPane #support-ticket-comments-table {
        height: auto;
    }

    SupportTicketManagementTabPane #support-ticket-details {
        padding: 1;
        height: auto;
    }

    SupportTicketManagementTabPane #support-ticket-comment-detail-scroll {
        height: 100%;
    }

    SupportTicketManagementTabPane #support-ticket-comment-detail {
        padding: 1;
        height: auto;
    }

    SupportTicketManagementTabPane #support-ticket-actions {
        height: auto;
        padding: 0 1;
        background: $surface;
    }

    SupportTicketManagementTabPane #comment-actions {
        height: auto;
        padding: 0 1;
        background: $surface;
    }

    SupportTicketManagementTabPane Button {
        min-width: 16;
    }
    """

    selected_ticket: reactive[Optional[SupportTicket]] = reactive(None)
    selected_comment: reactive[Optional[Comment]] = reactive(None)
    current_comments: List[Comment] = []

    def __init__(self, ctx: Optional[typer.Context] = None, **kwargs):
        super().__init__("🎫 Support", id="support-ticket-tab", **kwargs)
        self.ctx = ctx
        self.support_ticket_sdk = SupportTicketSDK()
        self.tickets: List[SupportTicket] = []

    def compose(self) -> ComposeResult:
        """Create the support ticket management layout with 3 horizontal panels."""
        with Vertical():
            yield Static("🎫 Support Ticket Management", classes="section-header")

            # Filters
            with Horizontal(id="support-ticket-filters"):
                yield Label("Status:")
                yield Select(
                    options=[
                        ("All", "all"),
                        ("Open", TicketStatus.OPEN.value),
                        ("In Progress", TicketStatus.IN_PROGRESS.value),
                        ("Closed", TicketStatus.CLOSED.value),
                    ],
                    value="all",
                    id="status-filter",
                )
                yield Label("Priority:")
                yield Select(
                    options=[
                        ("All", "all"),
                        ("Low", SeverityLevel.LOW.value),
                        ("Medium", SeverityLevel.MEDIUM.value),
                        ("High", SeverityLevel.HIGH.value),
                        ("Critical", SeverityLevel.CRITICAL.value),
                    ],
                    value="all",
                    id="priority-filter",
                )
                yield Button("🔄 Refresh", id="refresh-tickets-btn", variant="primary")

            # Main 3-panel horizontal layout
            with Horizontal(id="support-ticket-main-panel"):
                # Panel 1: Tickets List with Details
                with Vertical(id="tickets-panel"):
                    # Action buttons for tickets
                    with Horizontal(id="support-ticket-actions"):
                        yield Button("➕ Create Ticket", id="create-ticket-btn", variant="success")
                        yield Button(
                            "✏️ Update Ticket",
                            id="update-ticket-btn",
                            variant="primary",
                            disabled=True,
                        )
                    yield DataTable(
                        id="support-tickets-table", zebra_stripes=True, cursor_type="row"
                    )
                    yield Static("Select a ticket to view details", id="support-ticket-details")

                # Panel 2: Comments List
                with Vertical(id="comments-list-panel"):
                    # Action buttons for comments
                    with Horizontal(id="comment-actions"):
                        yield Button(
                            "➕ Add Comment",
                            id="create-comment-btn",
                            variant="success",
                            disabled=True,
                        )
                        yield Button(
                            "✏️ Update Comment",
                            id="update-comment-btn",
                            variant="primary",
                            disabled=True,
                        )
                    yield DataTable(
                        id="support-ticket-comments-table",
                        zebra_stripes=True,
                        cursor_type="row",
                        show_header=True,
                    )

                # Panel 3: Comment Detail Viewer
                with Vertical(id="comment-detail-panel"):
                    with ScrollableContainer(id="support-ticket-comment-detail-scroll"):
                        yield Static(
                            "Select a comment to view details", id="support-ticket-comment-detail"
                        )

    def on_mount(self) -> None:
        """Initialize the tab pane when mounted."""
        logger.debug("SupportTicketManagementTabPane mounted")

        # Setup the tickets table
        self.setup_tickets_table()

        # Setup the comments table
        self.setup_comments_table()

        # Set border titles for the panels
        self.query_one("#tickets-panel").border_title = "🎫 Tickets"
        self.query_one("#comments-list-panel").border_title = "💬 Comments"
        self.query_one("#comment-detail-panel").border_title = "👁️ Comment Detail"

        # Load tickets
        self.refresh_tickets()

    def setup_tickets_table(self) -> None:
        """Set up the support tickets table with columns."""
        try:
            tickets_table = self.query_one("#support-tickets-table", DataTable)
            tickets_table.clear(columns=True)

            # Add columns
            tickets_table.add_column("ID", key="id")
            tickets_table.add_column("Title", key="title")
            tickets_table.add_column("Status", key="status")
            tickets_table.add_column("Priority", key="priority")
            tickets_table.add_column("Created", key="created_at")

            tickets_table.cursor_type = "row"
            tickets_table.show_cursor = True

            logger.debug("Support tickets table setup complete.")
        except Exception as e:
            logger.error(f"Failed to setup tickets table: {e}")

    def setup_comments_table(self) -> None:
        """Set up the comments table with columns."""
        try:
            comments_table = self.query_one("#support-ticket-comments-table", DataTable)
            comments_table.clear(columns=True)

            # Add columns
            comments_table.add_column("User", key="user", width=20)
            comments_table.add_column("Time", key="time", width=20)

            comments_table.cursor_type = "row"
            comments_table.show_cursor = True

            logger.debug("Comments table setup complete.")
        except Exception as e:
            logger.error(f"Failed to setup comments table: {e}")

    @work(exclusive=True)
    async def load_ticket_comments(self, ticket_id: str) -> None:
        """Load and display comments for a specific ticket."""
        logger.debug(f"load_ticket_comments called for ticket {ticket_id}")

        if not self.ctx:
            logger.warning("No context available for loading comments")
            return

        try:
            # Get the comments table
            comments_table = self.query_one("#support-ticket-comments-table", DataTable)
            logger.debug("Found comments table, clearing it")
            comments_table.clear()

            # Fetch comments from API
            logger.debug(f"Fetching comments for ticket {ticket_id}")
            comments = await self.support_ticket_sdk.list_comments(self.ctx, ticket_id)
            logger.debug(f"Received {len(comments) if comments else 0} comments")

            # Store comments for later use
            self.current_comments = comments if comments else []

            if not comments:
                logger.debug("No comments found, adding placeholder")
                comments_table.add_row("No comments", "")
                # Clear the detail view
                comment_detail = self.query_one("#support-ticket-comment-detail", Static)
                comment_detail.update("No comments for this ticket yet.")
                return

            # Add comments to the table
            for idx, comment in enumerate(comments):
                # Format timestamp
                created_time = comment.created_at or "Unknown"
                if created_time != "Unknown":
                    try:
                        from datetime import datetime

                        dt = datetime.fromisoformat(created_time.replace("Z", "+00:00"))
                        created_time = dt.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        pass

                user_email = comment.user_email or "Unknown"

                logger.debug(f"Adding comment {idx + 1}: user={user_email}, time={created_time}")
                comments_table.add_row(
                    user_email,
                    created_time,
                    key=str(idx),  # Use index as key to identify comment later
                )

            logger.debug(
                f"Successfully loaded {len(comments)} comments for ticket {ticket_id} into table"
            )

        except Exception as e:
            logger.error(f"Failed to load comments for ticket {ticket_id}: {e}")
            import traceback

            logger.error(traceback.format_exc())
            # Show error in the comment detail
            try:
                comment_detail = self.query_one("#support-ticket-comment-detail", Static)
                comment_detail.update(f"[red]Error loading comments:[/red] {str(e)}")
            except Exception:
                pass

    @work(exclusive=True)
    async def refresh_tickets(self) -> None:
        """Refresh the tickets list from the API."""
        logger.debug("Starting ticket refresh...")

        if not self.ctx:
            logger.warning("No context available for ticket refresh")
            return

        try:
            # Get filter values
            status_filter = self.query_one("#status-filter", Select)
            priority_filter = self.query_one("#priority-filter", Select)

            status = None if str(status_filter.value) == "all" else str(status_filter.value)
            priority = None if str(priority_filter.value) == "all" else str(priority_filter.value)

            # Fetch tickets from API
            self.tickets = await self.support_ticket_sdk.list_tickets(
                ctx=self.ctx,
                status=status,
                priority=priority,
            )

            logger.debug(f"Fetched {len(self.tickets)} tickets")

            # Update the table
            self.update_tickets_table(self.tickets)

            logger.debug("Ticket refresh completed successfully")
        except Exception as e:
            logger.error(f"Failed to refresh tickets: {e}")
            self.notify(f"Failed to refresh tickets: {str(e)}", severity="error")

    def update_tickets_table(self, tickets: List[SupportTicket]) -> None:
        """Update the tickets table with the provided tickets."""
        try:
            tickets_table = self.query_one("#support-tickets-table", DataTable)
            tickets_table.clear()

            logger.debug(f"Updating tickets table with {len(tickets)} tickets")

            if not tickets:
                logger.debug("No tickets to display")
                # Add a placeholder row to show the table is working
                tickets_table.add_row(
                    "(No tickets)", "No support tickets found", "-", "-", "-", key="empty"
                )
                return

            for ticket in tickets:
                # Format created_at
                created_at = ticket.created_at or "N/A"
                if created_at != "N/A" and len(created_at) > 10:
                    created_at = created_at[:10]  # Just show date

                # Get the enum values properly
                status_display = ticket.status.value if ticket.status else "open"
                priority_display = ticket.priority.value if ticket.priority else "medium"

                tickets_table.add_row(
                    ticket.id[:8] if len(ticket.id) > 8 else ticket.id,
                    ticket.title,
                    status_display,
                    priority_display,
                    created_at,
                    key=ticket.id,
                )

            logger.debug(f"Tickets table now has {tickets_table.row_count} rows")
        except Exception as e:
            logger.error(f"Failed to update tickets table: {e}")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in either the tickets or comments table."""
        logger.debug(f"Row selected: table_id={event.data_table.id}, row_key={event.row_key}")

        # Check if this is the comments table
        if event.data_table.id == "support-ticket-comments-table":
            try:
                # Get the actual key value from the RowKey object
                row_key_value = (
                    event.row_key.value if hasattr(event.row_key, "value") else str(event.row_key)
                )
                row_key_str = str(row_key_value)

                # Skip if no key (placeholder row) or not a valid number
                if row_key_str == "None" or not row_key_str.isdigit():
                    logger.debug(f"Skipping placeholder row selection (key: {row_key_str})")
                    return

                # Get the comment index from the row key
                comment_idx = int(row_key_str)

                if 0 <= comment_idx < len(self.current_comments):
                    comment = self.current_comments[comment_idx]
                    self.selected_comment = comment

                    # Format the comment for display
                    user_email = comment.user_email or "Unknown"
                    created_time = comment.created_at or "Unknown"
                    if created_time != "Unknown":
                        try:
                            from datetime import datetime

                            dt = datetime.fromisoformat(created_time.replace("Z", "+00:00"))
                            created_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                        except Exception:
                            pass

                    raw_text = comment.raw_text or "No comment text"

                    # Update the comment detail view
                    comment_detail = self.query_one("#support-ticket-comment-detail", Static)
                    detail_text = f"[bold]User:[/bold] {user_email}\n"
                    detail_text += f"[bold]Time:[/bold] {created_time}\n\n"
                    detail_text += f"{raw_text}"
                    comment_detail.update(detail_text)

                    # Enable the update comment button
                    try:
                        update_comment_btn = self.query_one("#update-comment-btn", Button)
                        update_comment_btn.disabled = False
                    except Exception:
                        pass

                    logger.debug(f"Updated comment detail view for comment {comment_idx}")
            except Exception as e:
                logger.error(f"Failed to display comment: {e}")
                import traceback

                logger.error(traceback.format_exc())
            return

        # Otherwise, this is the tickets table
        try:
            # Get the selected ticket ID from the row key
            ticket_id = str(event.row_key.value)

            # Find the ticket in our list
            selected_ticket = next((t for t in self.tickets if t.id == ticket_id), None)

            if selected_ticket:
                self.selected_ticket = selected_ticket
                self.update_ticket_details(selected_ticket)

                # Enable the update ticket button
                try:
                    update_btn = self.query_one("#update-ticket-btn", Button)
                    update_btn.disabled = False
                except Exception:
                    pass

                # Enable the add comment button
                try:
                    create_comment_btn = self.query_one("#create-comment-btn", Button)
                    create_comment_btn.disabled = False
                except Exception:
                    pass

                # Load comments for this ticket
                logger.debug(f"Loading comments for ticket {ticket_id}")
                self.load_ticket_comments(ticket_id)

                logger.debug(f"Selected ticket: {ticket_id}")
        except Exception as e:
            logger.error(f"Failed to handle ticket selection: {e}")

    def update_ticket_details(self, ticket: SupportTicket) -> None:
        """Update the ticket details panel."""
        try:
            details_widget = self.query_one("#support-ticket-details", Static)

            # Get the enum values properly
            status_display = ticket.status.value if ticket.status else "open"
            priority_display = ticket.priority.value if ticket.priority else "medium"

            # Format the details
            details = f"""[bold]Ticket Details[/bold]

[cyan]ID:[/cyan] {ticket.id}
[cyan]Title:[/cyan] {ticket.title}
[cyan]Status:[/cyan] {status_display}
[cyan]Priority:[/cyan] {priority_display}

[bold]Description:[/bold]
{ticket.description or "No description"}

[cyan]User:[/cyan] {ticket.user_email or "N/A"}
[cyan]Assigned To:[/cyan] {ticket.assigned_to or "Unassigned"}
[cyan]Created:[/cyan] {ticket.created_at or "N/A"}
[cyan]Updated:[/cyan] {ticket.updated_at or "N/A"}
"""

            details_widget.update(details)
            logger.debug(f"Updated details for ticket: {ticket.id}")
        except Exception as e:
            logger.error(f"Failed to update ticket details: {e}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "create-ticket-btn":
            self.action_create_ticket()
        elif event.button.id == "update-ticket-btn":
            self.action_update_ticket()
        elif event.button.id == "refresh-tickets-btn":
            self.refresh_tickets()
        elif event.button.id == "create-comment-btn":
            self.action_create_comment()
        elif event.button.id == "update-comment-btn":
            self.action_update_comment()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle filter changes."""
        if event.select.id in ["status-filter", "priority-filter"]:
            logger.debug(f"Filter changed: {event.select.id} = {event.value}")
            self.refresh_tickets()

    def action_create_ticket(self) -> None:
        """Open the create ticket modal."""

        def handle_ticket_creation(ticket_data: Optional[dict]) -> None:
            if ticket_data:
                # Use a worker to create the ticket
                self.create_ticket_from_modal(ticket_data)

        self.app.push_screen(CreateSupportTicketModal(), handle_ticket_creation)

    @work(exclusive=True)
    async def create_ticket_from_modal(self, ticket_data: dict) -> None:
        """Create a new ticket from modal data."""
        if not self.ctx:
            self.notify("No context available", severity="error")
            return

        try:
            self.notify("Creating support ticket...", severity="information")

            # Create the ticket
            new_ticket = await self.support_ticket_sdk.create_ticket(
                ctx=self.ctx,
                title=ticket_data["title"],
                description=ticket_data["description"],
                priority=ticket_data["priority"],
            )

            self.notify(
                f"Successfully created ticket: {new_ticket.id}", severity="information", timeout=5
            )

            # Refresh the list
            self.refresh_tickets()

        except Exception as e:
            logger.error(f"Failed to create ticket: {e}")
            self.notify(f"Failed to create ticket: {str(e)}", severity="error")

    def action_update_ticket(self) -> None:
        """Open the update ticket modal."""
        if not self.selected_ticket:
            self.notify("Please select a ticket to update", severity="warning")
            return

        def handle_ticket_update(update_data: Optional[dict]) -> None:
            if update_data:
                # Call the @work decorated method directly - it returns a Worker that starts automatically
                self.update_ticket_from_modal(update_data)

        self.app.push_screen(UpdateSupportTicketModal(self.selected_ticket), handle_ticket_update)

    @work(exclusive=True)
    async def update_ticket_from_modal(self, update_data: dict) -> None:
        """Update a ticket from modal data."""
        if not self.ctx:
            self.notify("No context available", severity="error")
            return

        try:
            self.notify("Updating support ticket...", severity="information")

            # Update the ticket
            updated_ticket = await self.support_ticket_sdk.update_ticket(
                ctx=self.ctx,
                ticket_id=update_data["ticket_id"],
                title=update_data["title"],
                description=update_data["description"],
                status=update_data["status"],
                priority=update_data["priority"],
            )

            self.notify(
                f"Successfully updated ticket: {updated_ticket.id}",
                severity="information",
                timeout=5,
            )

            # Refresh the list
            self.refresh_tickets()

            # Update the selected ticket
            self.selected_ticket = updated_ticket
            self.update_ticket_details(updated_ticket)

        except Exception as e:
            logger.error(f"Failed to update ticket: {e}")
            self.notify(f"Failed to update ticket: {str(e)}", severity="error")

    def action_create_comment(self) -> None:
        """Open modal to create a new comment on the selected ticket."""
        if not self.selected_ticket:
            self.notify("Please select a ticket first", severity="warning")
            return

        def handle_comment_creation(comment_data: Optional[dict]) -> None:
            if comment_data:
                self.run_worker(self.create_comment_from_modal(comment_data))

        self.app.push_screen(CreateCommentModal(self.selected_ticket.id), handle_comment_creation)

    async def create_comment_from_modal(self, comment_data: dict) -> None:
        """Create a new comment from modal data.

        Args:
            comment_data: Dictionary containing comment data from modal
        """
        if not self.ctx:
            self.notify("No context available", severity="error")
            return

        try:
            # Create the comment using add_comment method
            logger.debug(f"Creating comment on ticket {comment_data['ticket_id']}")
            await self.support_ticket_sdk.add_comment(
                ctx=self.ctx,
                ticket_id=comment_data["ticket_id"],
                text=comment_data["comment_text"],
            )

            self.notify(
                "Comment added successfully", title="Success", severity="information", timeout=5
            )

            # Reload comments for the selected ticket
            if self.selected_ticket:
                self.load_ticket_comments(self.selected_ticket.id)

            # Also refresh the tickets list to update any metadata
            self.refresh_tickets()

        except Exception as e:
            logger.error(f"Failed to create comment: {e}")
            self.notify(f"Failed to create comment: {str(e)}", severity="error")

    def action_update_comment(self) -> None:
        """Open modal to update the selected comment."""
        if not self.selected_comment:
            self.notify("Please select a comment first", severity="warning")
            return

        def handle_comment_update(update_data: Optional[dict]) -> None:
            if update_data:
                self.run_worker(self.update_comment_from_modal(update_data))

        self.app.push_screen(UpdateCommentModal(self.selected_comment), handle_comment_update)

    async def update_comment_from_modal(self, update_data: dict) -> None:
        """Update a comment from modal data.

        Args:
            update_data: Dictionary containing comment update data from modal
        """
        if not self.ctx:
            self.notify("No context available", severity="error")
            return

        try:
            # Update the comment
            logger.debug(f"Updating comment {update_data['comment_id']}")
            await self.support_ticket_sdk.update_comment(
                ctx=self.ctx,
                comment_id=update_data["comment_id"],
                text=update_data["comment_text"],
            )

            self.notify(
                "Comment updated successfully", title="Success", severity="information", timeout=5
            )

            # Reload comments for the selected ticket
            if self.selected_ticket:
                self.load_ticket_comments(self.selected_ticket.id)

            # Also refresh the tickets list to update any metadata
            self.refresh_tickets()

        except Exception as e:
            logger.error(f"Failed to update comment: {e}")
            self.notify(f"Failed to update comment: {str(e)}", severity="error")
