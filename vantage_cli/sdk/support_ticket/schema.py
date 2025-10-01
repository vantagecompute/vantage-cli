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

from typing import Optional

from pydantic import BaseModel


class SupportTicket(BaseModel):
    """Schema for support ticket data."""

    id: str
    subject: str
    description: Optional[str] = None
    status: Optional[str] = None  # e.g., "open", "in_progress", "closed"
    priority: Optional[str] = None  # e.g., "low", "medium", "high", "critical"
    owner_email: Optional[str] = None
    assigned_to: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    resolved_at: Optional[str] = None
