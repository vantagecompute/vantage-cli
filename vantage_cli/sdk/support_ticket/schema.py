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
"""Support ticket schemas for the Vantage CLI."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class TicketStatus(str, Enum):
    """Ticket status values matching the SOS GraphQL API TicketStatus enum."""

    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    CLOSED = "CLOSED"


class SeverityLevel(str, Enum):
    """Severity level values matching the SOS GraphQL API SeverityLevel enum."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SupportTicket(BaseModel):
    """Schema for support ticket data.

    Matches the Tickets type from the SOS GraphQL API.
    API field mapping:
    - id: Int! (ticket ID)
    - title: String! (ticket subject/title)
    - description: String! (ticket description)
    - status: TicketStatus! (OPEN, IN_PROGRESS, CLOSED)
    - priority: SeverityLevel! (LOW, MEDIUM, HIGH, CRITICAL)
    - userEmail: String! (email of ticket creator)
    - assignedTo: String (email of assigned user, optional)
    - createdAt: DateTime!
    - updatedAt: DateTime!
    """

    id: str
    title: str  # API field: 'title'
    description: str
    status: TicketStatus  # API enum: OPEN, IN_PROGRESS, CLOSED
    priority: SeverityLevel  # API enum: LOW, MEDIUM, HIGH, CRITICAL
    user_email: str  # API field: 'userEmail'
    assigned_to: Optional[str] = None  # API field: 'assignedTo'
    created_at: str  # API field: 'createdAt'
    updated_at: str  # API field: 'updatedAt'


class Comment(BaseModel):
    """Schema for support ticket comment data.

    Matches the Comments type from the SOS GraphQL API.
    API field mapping:
    - id: Int! (comment ID)
    - ticketId: Int! (ID of the ticket this comment belongs to)
    - rawText: String! (comment text content)
    - userEmail: String! (email of comment author)
    - mentions: [String] (list of mentioned user emails)
    - attachments: [Attachments] (list of attached files)
    - createdAt: DateTime!
    - updatedAt: DateTime!
    """

    id: str
    ticket_id: str
    raw_text: str
    user_email: str
    mentions: Optional[List[str]] = None
    attachments: Optional[List["Attachment"]] = None
    created_at: str
    updated_at: str


class Attachment(BaseModel):
    """Schema for comment attachment data.

    Matches the Attachments type from the SOS GraphQL API.
    API field mapping:
    - id: Int! (attachment ID)
    - commentId: Int! (ID of the comment this attachment belongs to)
    - filename: String! (original filename)
    - type: String! (MIME type)
    - size: Int! (file size in bytes)
    - createdAt: DateTime!
    - updatedAt: DateTime!
    """

    id: str
    comment_id: str
    filename: str
    type: str  # MIME type
    size: int  # bytes
    created_at: str
    updated_at: str


# Update forward references
Comment.model_rebuild()
