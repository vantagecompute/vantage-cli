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
"""Support Ticket Management TabPane for Dashboard

A reusable TabPane widget for managing Vantage support tickets in the dashboard.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import typer
import logging

logger = logging.getLogger(__name__)
from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from textual.widgets import Button, DataTable, Input, Label, Static, TabPane, Select, TextArea
from textual.screen import ModalScreen

from vantage_cli.sdk.support_ticket.schema import SupportTicket, TicketStatus, SeverityLevel, Comment
from vantage_cli.sdk.support_ticket.crud import SupportTicketSDK



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
            yield Input(
                placeholder="Enter ticket title",
                id="ticket-title-input"
            )
            
            yield Label("Description:")
            yield TextArea(
                text="",
                id="ticket-description-input"
            )
            
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
            self.dismiss({
                "title": title,
                "description": description,
                "priority": priority,
            })
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
                value=self.ticket.title,
                placeholder="Enter ticket title",
                id="ticket-title-input"
            )
            
            yield Label("Description:")
            yield TextArea(
                text=self.ticket.description or "",
                id="ticket-description-input"
            )
            
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
            self.dismiss({
                "ticket_id": self.ticket.id,
                "title": title,
                "description": description,
                "status": status,
                "priority": priority,
            })
        elif event.button.id == "cancel-btn":
            self.dismiss(None)


class SupportTicketManagementTabPane(TabPane):
    """TabPane for managing support tickets with list on left and details on right."""
    
    DEFAULT_CSS = """
    SupportTicketManagementTabPane #support-ticket-details-section {
        height: 30%;
    }
    
    SupportTicketManagementTabPane #support-ticket-comments-section {
        height: 70%;
    }
    
    SupportTicketManagementTabPane #support-ticket-comments-list-section {
        width: 40%;
    }
    
    SupportTicketManagementTabPane #support-ticket-comment-detail-section {
        width: 60%;
    }
    
    SupportTicketManagementTabPane #support-ticket-comment-detail-scroll {
        height: 100%;
        border: solid $primary;
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
        """Create the tab pane layout."""
        yield Static("🎫 Support Ticket Management", classes="section-header")
        
        # Status and refresh section
        with Horizontal(id="support-ticket-status-bar"):
            yield Static("Status: Ready", id="ticket-status")
            yield Button("🔄 Update", id="refresh-tickets-btn", variant="primary")
        
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
        
        # Main content area - split into left and right panels
        with Horizontal(id="support-ticket-content"):
            # Left panel: Ticket list
            with Vertical(id="support-tickets-section"):
                yield Static("📋 Support Tickets", classes="subsection-header")
                yield DataTable(id="support-tickets-table", zebra_stripes=True, cursor_type="row")
            
            # Right panel: Ticket details and comments (vertically stacked)
            with Vertical(id="support-ticket-right-panel"):
                # Ticket details section
                with Vertical(id="support-ticket-details-section"):
                    yield Static("📄 Ticket Details", classes="subsection-header")
                    yield Static("Select a ticket to view details", id="support-ticket-details")
                
                # Comments section (split into comment list and comment detail)
                with Vertical(id="support-ticket-comments-section"):
                    yield Static("💬 Comments", classes="subsection-header")
                    with Horizontal(id="support-ticket-comments-content"):
                        # Comment list (left)
                        with Vertical(id="support-ticket-comments-list-section"):
                            yield DataTable(id="support-ticket-comments-table", zebra_stripes=True, cursor_type="row", show_header=True)
                        
                        # Comment detail (right)
                        with Vertical(id="support-ticket-comment-detail-section"):
                            with ScrollableContainer(id="support-ticket-comment-detail-scroll"):
                                yield Static("Select a comment to view details", id="support-ticket-comment-detail")
        
        # Action buttons
        with Horizontal(id="support-ticket-actions"):
            yield Button("➕ Create", id="create-ticket-btn", variant="success")
            yield Button("✏️ Update", id="update-ticket-btn", variant="primary", disabled=True)
    
    def on_mount(self) -> None:
        """Initialize the tab pane when mounted."""
        logger.debug("SupportTicketManagementTabPane mounted")
        
        # Setup the tickets table
        self.setup_tickets_table()
        
        # Setup the comments table
        self.setup_comments_table()
        
        # Load tickets
        self.refresh_tickets()
    
    def setup_tickets_table(self) -> None:
        """Setup the support tickets table with columns."""
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
        """Setup the comments table with columns."""
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
                        dt = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
                        created_time = dt.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        pass
                
                user_email = comment.user_email or "Unknown"
                
                logger.debug(f"Adding comment {idx+1}: user={user_email}, time={created_time}")
                comments_table.add_row(
                    user_email,
                    created_time,
                    key=str(idx)  # Use index as key to identify comment later
                )
            
            logger.debug(f"Successfully loaded {len(comments)} comments for ticket {ticket_id} into table")

            
        except Exception as e:
            logger.error(f"Failed to load comments for ticket {ticket_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Show error in the display
            try:
                comments_display = self.query_one("#support-ticket-comments-display", Static)
                comments_display.update(f"[red]Error loading comments:[/red] {str(e)}")
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
                    "(No tickets)",
                    "No support tickets found",
                    "-",
                    "-",
                    "-",
                    key="empty"
                )
                return
            
            for ticket in tickets:
                # Format created_at
                created_at = ticket.created_at or "N/A"
                if created_at != "N/A" and len(created_at) > 10:
                    created_at = created_at[:10]  # Just show date
                
                tickets_table.add_row(
                    ticket.id[:8] if len(ticket.id) > 8 else ticket.id,
                    ticket.title,
                    ticket.status.value,
                    ticket.priority.value,
                    created_at,
                    key=ticket.id,
                )
            
            logger.debug(f"Tickets table now has {tickets_table.row_count} rows")
        except Exception as e:
            logger.error(f"Failed to update tickets table: {e}")
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle ticket row selection."""
        try:
            # Get the selected ticket ID from the row key
            ticket_id = str(event.row_key.value)
            
            # Find the ticket in our list
            selected_ticket = next((t for t in self.tickets if t.id == ticket_id), None)
            
            if selected_ticket:
                self.selected_ticket = selected_ticket
                self.update_ticket_details(selected_ticket)
                
                # Load comments for the selected ticket
                self.load_ticket_comments(selected_ticket.id)
                
                # Enable the update button
                try:
                    update_btn = self.query_one("#update-ticket-btn", Button)
                    update_btn.disabled = False
                except Exception:
                    pass
                
                logger.debug(f"Selected ticket: {ticket_id}")
        except Exception as e:
            logger.error(f"Failed to handle ticket selection: {e}")
    
    def update_ticket_details(self, ticket: SupportTicket) -> None:
        """Update the ticket details panel."""
        try:
            details_widget = self.query_one("#support-ticket-details", Static)
            
            # Format the details
            details = f"""[bold]Ticket Details[/bold]

[cyan]ID:[/cyan] {ticket.id}
[cyan]Title:[/cyan] {ticket.title}
[cyan]Status:[/cyan] {ticket.status.value}
[cyan]Priority:[/cyan] {ticket.priority.value}

[bold]Description:[/bold]
{ticket.description or 'No description'}

[cyan]User:[/cyan] {ticket.user_email or 'N/A'}
[cyan]Assigned To:[/cyan] {ticket.assigned_to or 'Unassigned'}
[cyan]Created:[/cyan] {ticket.created_at or 'N/A'}
[cyan]Updated:[/cyan] {ticket.updated_at or 'N/A'}
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
                f"Successfully created ticket: {new_ticket.id}",
                severity="information",
                timeout=5
            )
            
            # Refresh the list
            await self.refresh_tickets()
            
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
                # The @work decorator on update_ticket_from_modal makes it return a Worker
                # Just call it directly - no need for run_worker or await
                self.update_ticket_from_modal(update_data)
        
        self.app.push_screen(
            UpdateSupportTicketModal(self.selected_ticket),
            handle_ticket_update
        )
    
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
                timeout=5
            )
            
            # Refresh the list - just call it to start the worker, don't await
            self.refresh_tickets()
            
            # Update the selected ticket
            self.selected_ticket = updated_ticket
            self.update_ticket_details(updated_ticket)
            
        except Exception as e:
            logger.error(f"Failed to update ticket: {e}")
            self.notify(f"Failed to update ticket: {str(e)}", severity="error")
