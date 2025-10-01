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
"""CRUD operations for support tickets using GraphQL."""

from typing import Any, Dict, List, Optional

import typer
from loguru import logger

from vantage_cli.exceptions import Abort
from vantage_cli.gql_client import create_async_graphql_client
from vantage_cli.schemas import SupportTicket


class SupportTicketSDK:
    """SDK for support ticket operations."""

    async def list_tickets(
        self,
        ctx: typer.Context,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[SupportTicket]:
        """List all support tickets.

        Args:
            ctx: Typer context containing settings and profile
            status: Optional status filter
            priority: Optional priority filter
            limit: Maximum number of tickets to return

        Returns:
            List of SupportTicket objects
        """
        query = """
        query SupportTickets($first: Int) {
            supportTickets(first: $first) {
                edges {
                    node {
                        id
                        subject
                        description
                        status
                        priority
                        ownerEmail
                        assignedTo
                        createdAt
                        updatedAt
                        resolvedAt
                    }
                }
                total
            }
        }
        """

        variables: Dict[str, Any] = {}
        if limit:
            variables["first"] = limit
        else:
            variables["first"] = 100  # Default limit

        try:
            # Create async GraphQL client
            profile = getattr(ctx.obj, "profile", "default")
            graphql_client = create_async_graphql_client(ctx.obj.settings, profile)

            # Execute the query
            logger.debug(
                f"Executing GraphQL query to list support tickets with variables: {variables}"
            )
            response_data = await graphql_client.execute_async(query, variables)

            if not response_data:
                logger.warning("No response from GraphQL server for support tickets")
                # Return empty list if no response (API might not be implemented yet)
                return []

            tickets_data = response_data.get("supportTickets", {})
            tickets_list = [edge["node"] for edge in tickets_data.get("edges", [])]

            # Apply client-side filters if provided
            if status:
                tickets_list = [t for t in tickets_list if t.get("status") == status]
            if priority:
                tickets_list = [t for t in tickets_list if t.get("priority") == priority]

            # Convert to SupportTicket objects with proper field mapping
            tickets = []
            for ticket_dict in tickets_list:
                ticket = SupportTicket(
                    id=ticket_dict.get("id", ""),
                    subject=ticket_dict.get("subject", ""),
                    description=ticket_dict.get("description"),
                    status=ticket_dict.get("status"),
                    priority=ticket_dict.get("priority"),
                    owner_email=ticket_dict.get("ownerEmail"),
                    assigned_to=ticket_dict.get("assignedTo"),
                    created_at=ticket_dict.get("createdAt"),
                    updated_at=ticket_dict.get("updatedAt"),
                    resolved_at=ticket_dict.get("resolvedAt"),
                )
                tickets.append(ticket)

            logger.debug(f"Successfully retrieved {len(tickets)} support tickets")
            return tickets

        except Exception as e:
            # If the GraphQL endpoint doesn't exist yet, return empty list gracefully
            if "GraphQL errors" in str(e) or "Cannot query field" in str(e):
                logger.warning(f"Support ticket API not available: {e}")
                return []
            logger.error(f"Failed to list support tickets: {e}")
            raise Abort(
                f"Failed to list support tickets: {e}",
                subject="Query Failed",
                log_message=f"GraphQL query failed: {e}",
            )

    async def get_ticket(
        self,
        ctx: typer.Context,
        ticket_id: str,
    ) -> Optional[SupportTicket]:
        """Get a specific support ticket by ID.

        Args:
            ctx: Typer context containing settings and profile
            ticket_id: ID of the support ticket

        Returns:
            SupportTicket object if found, None otherwise
        """
        query = """
        query SupportTicket($id: ID!) {
            supportTicket(id: $id) {
                id
                subject
                description
                status
                priority
                ownerEmail
                assignedTo
                createdAt
                updatedAt
                resolvedAt
            }
        }
        """

        variables: Dict[str, Any] = {"id": ticket_id}

        try:
            # Create async GraphQL client
            profile = getattr(ctx.obj, "profile", "default")
            graphql_client = create_async_graphql_client(ctx.obj.settings, profile)

            # Execute the query
            logger.debug(f"Executing GraphQL query to get support ticket '{ticket_id}'")
            response_data = await graphql_client.execute_async(query, variables)

            if not response_data or not response_data.get("supportTicket"):
                logger.debug(f"Support ticket '{ticket_id}' not found")
                return None

            ticket_dict = response_data["supportTicket"]

            # Map to SupportTicket object
            ticket = SupportTicket(
                id=ticket_dict.get("id", ""),
                subject=ticket_dict.get("subject", ""),
                description=ticket_dict.get("description"),
                status=ticket_dict.get("status"),
                priority=ticket_dict.get("priority"),
                owner_email=ticket_dict.get("ownerEmail"),
                assigned_to=ticket_dict.get("assignedTo"),
                created_at=ticket_dict.get("createdAt"),
                updated_at=ticket_dict.get("updatedAt"),
                resolved_at=ticket_dict.get("resolvedAt"),
            )

            logger.debug(f"Successfully retrieved support ticket '{ticket_id}'")
            return ticket

        except Exception as e:
            # If the GraphQL endpoint doesn't exist yet, return None gracefully
            if "GraphQL errors" in str(e) or "Cannot query field" in str(e):
                logger.warning(f"Support ticket API not available: {e}")
                return None
            logger.error(f"Failed to get support ticket '{ticket_id}': {e}")
            raise Abort(
                f"Failed to get support ticket: {e}",
                subject="Query Failed",
                log_message=f"GraphQL query failed: {e}",
            )

    async def create_ticket(
        self,
        ctx: typer.Context,
        subject: str,
        description: str,
        priority: Optional[str] = "medium",
    ) -> SupportTicket:
        """Create a new support ticket.

        Args:
            ctx: Typer context containing settings and profile
            subject: Ticket subject
            description: Ticket description
            priority: Ticket priority (default: medium)

        Returns:
            Created SupportTicket object
        """
        mutation = """
        mutation CreateSupportTicket($input: CreateSupportTicketInput!) {
            createSupportTicket(input: $input) {
                id
                subject
                description
                status
                priority
                ownerEmail
                assignedTo
                createdAt
                updatedAt
                resolvedAt
            }
        }
        """

        variables: Dict[str, Any] = {
            "input": {
                "subject": subject,
                "description": description,
                "priority": priority,
            }
        }

        try:
            # Create async GraphQL client
            profile = getattr(ctx.obj, "profile", "default")
            graphql_client = create_async_graphql_client(ctx.obj.settings, profile)

            # Execute the mutation
            logger.debug("Executing GraphQL mutation to create support ticket")
            response_data = await graphql_client.execute_async(mutation, variables)

            if not response_data or not response_data.get("createSupportTicket"):
                raise Abort(
                    "Failed to create support ticket: No response from server",
                    subject="Mutation Failed",
                    log_message="GraphQL mutation returned no data",
                )

            ticket_dict = response_data["createSupportTicket"]

            # Map to SupportTicket object
            ticket = SupportTicket(
                id=ticket_dict.get("id", ""),
                subject=ticket_dict.get("subject", ""),
                description=ticket_dict.get("description"),
                status=ticket_dict.get("status"),
                priority=ticket_dict.get("priority"),
                owner_email=ticket_dict.get("ownerEmail"),
                assigned_to=ticket_dict.get("assignedTo"),
                created_at=ticket_dict.get("createdAt"),
                updated_at=ticket_dict.get("updatedAt"),
                resolved_at=ticket_dict.get("resolvedAt"),
            )

            logger.debug(f"Successfully created support ticket '{ticket.id}'")
            return ticket

        except Abort:
            raise
        except Exception as e:
            logger.error(f"Failed to create support ticket: {e}")
            raise Abort(
                f"Failed to create support ticket: {e}",
                subject="Mutation Failed",
                log_message=f"GraphQL mutation failed: {e}",
            )

    async def update_ticket(
        self,
        ctx: typer.Context,
        ticket_id: str,
        subject: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> SupportTicket:
        """Update an existing support ticket.

        Args:
            ctx: Typer context containing settings and profile
            ticket_id: ID of the ticket to update
            subject: New subject (optional)
            description: New description (optional)
            status: New status (optional)
            priority: New priority (optional)

        Returns:
            Updated SupportTicket object
        """
        mutation = """
        mutation UpdateSupportTicket($id: ID!, $input: UpdateSupportTicketInput!) {
            updateSupportTicket(id: $id, input: $input) {
                id
                subject
                description
                status
                priority
                ownerEmail
                assignedTo
                createdAt
                updatedAt
                resolvedAt
            }
        }
        """

        # Build input with only provided fields
        input_data: Dict[str, Any] = {}
        if subject is not None:
            input_data["subject"] = subject
        if description is not None:
            input_data["description"] = description
        if status is not None:
            input_data["status"] = status
        if priority is not None:
            input_data["priority"] = priority

        variables: Dict[str, Any] = {
            "id": ticket_id,
            "input": input_data,
        }

        try:
            # Create async GraphQL client
            profile = getattr(ctx.obj, "profile", "default")
            graphql_client = create_async_graphql_client(ctx.obj.settings, profile)

            # Execute the mutation
            logger.debug(f"Executing GraphQL mutation to update support ticket '{ticket_id}'")
            response_data = await graphql_client.execute_async(mutation, variables)

            if not response_data or not response_data.get("updateSupportTicket"):
                raise Abort(
                    f"Failed to update support ticket '{ticket_id}': No response from server",
                    subject="Mutation Failed",
                    log_message="GraphQL mutation returned no data",
                )

            ticket_dict = response_data["updateSupportTicket"]

            # Map to SupportTicket object
            ticket = SupportTicket(
                id=ticket_dict.get("id", ""),
                subject=ticket_dict.get("subject", ""),
                description=ticket_dict.get("description"),
                status=ticket_dict.get("status"),
                priority=ticket_dict.get("priority"),
                owner_email=ticket_dict.get("ownerEmail"),
                assigned_to=ticket_dict.get("assignedTo"),
                created_at=ticket_dict.get("createdAt"),
                updated_at=ticket_dict.get("updatedAt"),
                resolved_at=ticket_dict.get("resolvedAt"),
            )

            logger.debug(f"Successfully updated support ticket '{ticket_id}'")
            return ticket

        except Abort:
            raise
        except Exception as e:
            logger.error(f"Failed to update support ticket '{ticket_id}': {e}")
            raise Abort(
                f"Failed to update support ticket: {e}",
                subject="Mutation Failed",
                log_message=f"GraphQL mutation failed: {e}",
            )

    async def delete_ticket(
        self,
        ctx: typer.Context,
        ticket_id: str,
    ) -> bool:
        """Delete a support ticket.

        Args:
            ctx: Typer context containing settings and profile
            ticket_id: ID of the ticket to delete

        Returns:
            True if deletion was successful
        """
        mutation = """
        mutation DeleteSupportTicket($id: ID!) {
            deleteSupportTicket(id: $id) {
                success
            }
        }
        """

        variables: Dict[str, Any] = {"id": ticket_id}

        try:
            # Create async GraphQL client
            profile = getattr(ctx.obj, "profile", "default")
            graphql_client = create_async_graphql_client(ctx.obj.settings, profile)

            # Execute the mutation
            logger.debug(f"Executing GraphQL mutation to delete support ticket '{ticket_id}'")
            response_data = await graphql_client.execute_async(mutation, variables)

            if not response_data or not response_data.get("deleteSupportTicket"):
                raise Abort(
                    f"Failed to delete support ticket '{ticket_id}': No response from server",
                    subject="Mutation Failed",
                    log_message="GraphQL mutation returned no data",
                )

            success = response_data["deleteSupportTicket"].get("success", False)

            if success:
                logger.debug(f"Successfully deleted support ticket '{ticket_id}'")
            else:
                logger.warning(f"Delete operation returned success=False for ticket '{ticket_id}'")

            return success

        except Abort:
            raise
        except Exception as e:
            logger.error(f"Failed to delete support ticket '{ticket_id}': {e}")
            raise Abort(
                f"Failed to delete support ticket: {e}",
                subject="Mutation Failed",
                log_message=f"GraphQL mutation failed: {e}",
            )


# Global singleton instance
support_ticket_sdk = SupportTicketSDK()
