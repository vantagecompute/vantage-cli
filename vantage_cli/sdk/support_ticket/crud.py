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
"""Support ticket CRUD operations using GraphQL API."""

import logging
from typing import Any, Dict, List, Optional

import typer

from vantage_cli.exceptions import Abort
from vantage_cli.gql_client import VantageGQLClient, VantageGraphQLClient
from vantage_cli.schemas import CliContext
from vantage_cli.sdk.support_ticket.schema import (
    Comment,
    SeverityLevel,
    SupportTicket,
    TicketStatus,
)

logger = logging.getLogger(__name__)


class SupportTicketSDK:
    """SDK for support ticket operations."""

    def _get_graphql_client(self, ctx: typer.Context) -> VantageGraphQLClient:
        """Get or create a GraphQL client for SOS API.

        Args:
            ctx: Typer context or CliContext

        Returns:
            VantageGraphQLClient instance configured for SOS API
        """
        # Check if this is a typer.Context with obj.graphql_client
        if hasattr(ctx, "obj") and hasattr(ctx.obj, "graphql_client"):
            return ctx.obj.graphql_client

        # Otherwise, create a new GraphQL client for SOS API
        # This handles the dashboard case where ctx is a CliContext
        if isinstance(ctx, CliContext):
            # Create GraphQL client with SOS endpoint
            if ctx.settings is None:
                raise ValueError("Settings not available in context")
            factory = VantageGQLClient(
                settings=ctx.settings, profile=ctx.profile, base_path="/sos/graphql"
            )
            return factory.create()
        elif hasattr(ctx, "obj") and isinstance(ctx.obj, CliContext):
            # Handle typer.Context wrapping CliContext
            if ctx.obj.settings is None:
                raise ValueError("Settings not available in context")
            factory = VantageGQLClient(
                settings=ctx.obj.settings, profile=ctx.obj.profile, base_path="/sos/graphql"
            )
            return factory.create()
        else:
            raise ValueError("Context must be typer.Context or CliContext")

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
            tickets(first: $first) {
                edges {
                    node {
                        id
                        title
                        description
                        status
                        priority
                        userEmail
                        assignedTo
                        createdAt
                        updatedAt
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
            # Get GraphQL client (handles both CLI and dashboard contexts)
            graphql_client = self._get_graphql_client(ctx)

            # Execute the query
            logger.debug(
                f"Executing GraphQL query to list support tickets with variables: {variables}"
            )
            response_data = await graphql_client.execute_async(query, variables)

            if not response_data:
                logger.warning("No response from GraphQL server for support tickets")
                # Return empty list if no response (API might not be implemented yet)
                return []

            tickets_data = response_data.get("tickets", {})
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
                    id=str(ticket_dict.get("id", "")),
                    title=ticket_dict.get("title", ""),
                    description=ticket_dict.get("description", ""),
                    status=TicketStatus(ticket_dict.get("status", TicketStatus.OPEN.value)),
                    priority=SeverityLevel(
                        ticket_dict.get("priority", SeverityLevel.MEDIUM.value)
                    ),
                    user_email=ticket_dict.get("userEmail", ""),
                    assigned_to=ticket_dict.get("assignedTo"),
                    created_at=ticket_dict.get("createdAt", ""),
                    updated_at=ticket_dict.get("updatedAt", ""),
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
        # Use the tickets query and filter by ID
        # The API doesn't have a singular 'ticket' query
        tickets = await self.list_tickets(ctx, limit=1000)  # Get all tickets

        # Find the ticket with matching ID
        for ticket in tickets:
            if ticket.id == str(ticket_id):
                logger.debug(f"Successfully retrieved support ticket '{ticket_id}'")
                return ticket

        logger.debug(f"Support ticket '{ticket_id}' not found")
        return None

    async def create_ticket(
        self,
        ctx: typer.Context,
        title: str,
        description: str,
        priority: Optional[str] = "MEDIUM",
    ) -> SupportTicket:
        """Create a new support ticket.

        Args:
            ctx: Typer context containing settings and profile
            title: Ticket title
            description: Ticket description
            priority: Ticket priority (default: MEDIUM)

        Returns:
            Created SupportTicket object
        """
        mutation = """
        mutation CreateTicket($input: CreateSupportTicket!) {
            createSupportTicket(createSupportTicketInput: $input) {
                id
                title
                description
                status
                priority
                userEmail
                assignedTo
                createdAt
                updatedAt
            }
        }
        """

        variables: Dict[str, Any] = {
            "input": {
                "title": title,
                "description": description,
                "priority": priority if priority else SeverityLevel.MEDIUM.value,
            }
        }

        try:
            # Use GraphQL client from context
            graphql_client = self._get_graphql_client(ctx)

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
                id=str(ticket_dict.get("id", "")),
                title=ticket_dict.get("title", ""),
                description=ticket_dict.get("description", ""),
                status=TicketStatus(ticket_dict.get("status", TicketStatus.OPEN.value)),
                priority=SeverityLevel(ticket_dict.get("priority", SeverityLevel.MEDIUM.value)),
                user_email=ticket_dict.get("userEmail", ""),
                assigned_to=ticket_dict.get("assignedTo"),
                created_at=ticket_dict.get("createdAt", ""),
                updated_at=ticket_dict.get("updatedAt", ""),
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
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> SupportTicket:
        """Update an existing support ticket.

        Args:
            ctx: Typer context containing settings and profile
            ticket_id: ID of the ticket to update
            title: New title (optional)
            description: New description (optional)
            status: New status (optional)
            priority: New priority (optional)

        Returns:
            Updated SupportTicket object
        """
        mutation = """
        mutation UpdateTicket($ticketId: Int!, $updateSupportTicketInput: UpdateSupportTicket!) {
            updateSupportTicket(ticketId: $ticketId, updateSupportTicketInput: $updateSupportTicketInput) {
                message
            }
        }
        """

        # Build input with only provided fields
        # Note: Backend only accepts description in UpdateSupportTicket input
        input_data: Dict[str, Any] = {}
        if description is not None:
            input_data["description"] = description

        # TODO: title, status, and priority might need separate mutation or different approach
        if title is not None:
            logger.warning("Updating title is not currently supported by the backend")
        if status is not None:
            logger.warning("Updating status is not currently supported by the backend")
        if priority is not None:
            logger.warning("Updating priority is not currently supported by the backend")

        variables: Dict[str, Any] = {
            "ticketId": int(ticket_id),
            "updateSupportTicketInput": input_data,
        }

        try:
            # Use GraphQL client from context
            graphql_client = self._get_graphql_client(ctx)

            # Execute the mutation
            logger.debug(f"Executing GraphQL mutation to update support ticket '{ticket_id}'")
            response_data = await graphql_client.execute_async(mutation, variables)

            if not response_data or not response_data.get("updateSupportTicket"):
                raise Abort(
                    f"Failed to update support ticket '{ticket_id}': No response from server",
                    subject="Mutation Failed",
                    log_message="GraphQL mutation returned no data",
                )

            update_response = response_data["updateSupportTicket"]
            message = update_response.get("message", "")
            logger.debug(f"Update response: {message}")

            # Refetch the ticket to get updated data
            # The mutation only returns a message, not the full ticket object
            updated_ticket = await self.get_ticket(ctx, ticket_id)

            if not updated_ticket:
                raise Abort(
                    f"Failed to retrieve updated ticket '{ticket_id}' after update",
                    subject="Refetch Failed",
                    log_message="Could not retrieve ticket after successful update",
                )

            logger.debug(f"Successfully updated support ticket '{ticket_id}'")
            return updated_ticket

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
            # Use GraphQL client from context
            graphql_client = self._get_graphql_client(ctx)

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

    async def list_comments(
        self,
        ctx: typer.Context,
        ticket_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Comment]:
        """List comments for a ticket or all comments.

        Args:
            ctx: Typer context containing graphql_client
            ticket_id: Optional ticket ID to filter comments
            limit: Maximum number of comments to return

        Returns:
            List of Comment objects
        """
        query = """
        query Comments($first: Int, $filters: JSONScalar) {
            comments(first: $first, filters: $filters) {
                edges {
                    node {
                        id
                        ticketId
                        rawText
                        userEmail
                        mentions
                        createdAt
                        updatedAt
                    }
                }
            }
        }
        """

        variables: Dict[str, Any] = {}
        if limit:
            variables["first"] = limit
        else:
            variables["first"] = 100

        if ticket_id:
            variables["filters"] = {"ticketId": {"eq": int(ticket_id)}}

        try:
            graphql_client = self._get_graphql_client(ctx)
            logger.debug("Executing GraphQL query to list comments")
            response_data = await graphql_client.execute_async(query, variables)

            if not response_data:
                return []

            comments_data = response_data.get("comments", {})
            comments_list = [edge["node"] for edge in comments_data.get("edges", [])]

            comments = []
            for comment_dict in comments_list:
                comment = Comment(
                    id=str(comment_dict.get("id", "")),
                    ticket_id=str(comment_dict.get("ticketId", "")),
                    raw_text=comment_dict.get("rawText", ""),
                    user_email=comment_dict.get("userEmail", ""),
                    mentions=comment_dict.get("mentions", []),
                    attachments=[],  # Will be populated separately if needed
                    created_at=comment_dict.get("createdAt", ""),
                    updated_at=comment_dict.get("updatedAt", ""),
                )
                comments.append(comment)

            logger.debug(f"Successfully retrieved {len(comments)} comments")
            return comments

        except Exception as e:
            logger.error(f"Failed to list comments: {e}")
            raise Abort(
                f"Failed to list comments: {e}",
                subject="Query Failed",
                log_message=f"GraphQL query failed: {e}",
            )

    async def add_comment(
        self,
        ctx: typer.Context,
        ticket_id: str,
        text: str,
        mentions: Optional[List[str]] = None,
    ) -> Comment:
        """Add a comment to a support ticket.

        Args:
            ctx: Typer context containing graphql_client
            ticket_id: ID of the ticket to comment on
            text: Comment text content
            mentions: Optional list of user emails to mention

        Returns:
            Created Comment object
        """
        mutation = """
        mutation AddComment($ticketId: Int!, $input: AddCommentToTicket!) {
            addCommentToTicket(ticketId: $ticketId, addCommentToTicketInput: $input) {
                ... on Comments {
                    id
                    ticketId
                    rawText
                    userEmail
                    mentions
                    createdAt
                    updatedAt
                }
                ... on FileSizeLimitExceeded {
                    message
                }
            }
        }
        """

        variables: Dict[str, Any] = {
            "ticketId": int(ticket_id),
            "input": {
                "rawText": text,
                "mentions": mentions or [],
            },
        }

        try:
            graphql_client = self._get_graphql_client(ctx)
            logger.debug(f"Adding comment to ticket '{ticket_id}'")
            response_data = await graphql_client.execute_async(mutation, variables)

            if not response_data or not response_data.get("addCommentToTicket"):
                raise Abort(
                    "Failed to add comment: No response from server",
                    subject="Mutation Failed",
                    log_message="GraphQL mutation returned no data",
                )

            comment_dict = response_data["addCommentToTicket"]

            # Check if the response is an error (CommentsFileSizeLimitExceeded)
            if "message" in comment_dict and "id" not in comment_dict:
                raise Abort(
                    f"Failed to add comment: {comment_dict['message']}",
                    subject="Add Comment Failed",
                    log_message=f"Add comment error: {comment_dict['message']}",
                )

            comment = Comment(
                id=str(comment_dict.get("id", "")),
                ticket_id=str(comment_dict.get("ticketId", "")),
                raw_text=comment_dict.get("rawText", ""),
                user_email=comment_dict.get("userEmail", ""),
                mentions=comment_dict.get("mentions", []),
                attachments=[],
                created_at=comment_dict.get("createdAt", ""),
                updated_at=comment_dict.get("updatedAt", ""),
            )

            logger.debug(f"Successfully added comment to ticket '{ticket_id}'")
            return comment

        except Abort:
            raise
        except Exception as e:
            logger.error(f"Failed to add comment: {e}")
            raise Abort(
                f"Failed to add comment: {e}",
                subject="Mutation Failed",
                log_message=f"GraphQL mutation failed: {e}",
            )

    async def update_comment(
        self,
        ctx: typer.Context,
        comment_id: str,
        text: str,
        mentions: Optional[List[str]] = None,
    ) -> Comment:
        """Update a comment's text.

        Args:
            ctx: Typer context containing graphql_client
            comment_id: ID of the comment to update
            text: New comment text
            mentions: Optional list of user emails to mention

        Returns:
            Updated Comment object
        """
        mutation = """
        mutation UpdateComment($commentId: Int!, $rawText: String!, $mentions: [String!]) {
            updateCommentText(commentId: $commentId, rawText: $rawText, mentions: $mentions) {
                ... on Comments {
                    id
                    ticketId
                    rawText
                    userEmail
                    mentions
                    createdAt
                    updatedAt
                }
                ... on CommentNotFound {
                    message
                }
            }
        }
        """

        variables: Dict[str, Any] = {
            "commentId": int(comment_id),
            "rawText": text,
            "mentions": mentions or [],
        }

        try:
            graphql_client = self._get_graphql_client(ctx)
            logger.debug(f"Updating comment '{comment_id}'")
            response_data = await graphql_client.execute_async(mutation, variables)

            if not response_data or not response_data.get("updateCommentText"):
                raise Abort(
                    "Failed to update comment: No response from server",
                    subject="Mutation Failed",
                    log_message="GraphQL mutation returned no data",
                )

            comment_dict = response_data["updateCommentText"]

            # Check if the response is an error (CommentsCommentNotFound)
            if "message" in comment_dict and "id" not in comment_dict:
                raise Abort(
                    f"Failed to update comment: {comment_dict['message']}",
                    subject="Comment Not Found",
                    log_message=f"Comment not found: {comment_dict['message']}",
                )

            comment = Comment(
                id=str(comment_dict.get("id", "")),
                ticket_id=str(comment_dict.get("ticketId", "")),
                raw_text=comment_dict.get("rawText", ""),
                user_email=comment_dict.get("userEmail", ""),
                mentions=comment_dict.get("mentions", []),
                attachments=[],
                created_at=comment_dict.get("createdAt", ""),
                updated_at=comment_dict.get("updatedAt", ""),
            )

            logger.debug(f"Successfully updated comment '{comment_id}'")
            return comment

        except Abort:
            raise
        except Exception as e:
            logger.error(f"Failed to update comment: {e}")
            raise Abort(
                f"Failed to update comment: {e}",
                subject="Mutation Failed",
                log_message=f"GraphQL mutation failed: {e}",
            )

    async def delete_comment(
        self,
        ctx: typer.Context,
        comment_id: str,
    ) -> bool:
        """Delete a comment.

        Args:
            ctx: Typer context containing graphql_client
            comment_id: ID of the comment to delete

        Returns:
            True if deletion was successful
        """
        mutation = """
        mutation DeleteComment($commentId: Int!) {
            deleteComment(commentId: $commentId)
        }
        """

        variables: Dict[str, Any] = {"commentId": int(comment_id)}

        try:
            graphql_client = self._get_graphql_client(ctx)
            logger.debug(f"Deleting comment '{comment_id}'")
            response_data = await graphql_client.execute_async(mutation, variables)

            success = response_data.get("deleteComment", False)
            logger.debug(f"Comment '{comment_id}' deleted: {success}")
            return bool(success)

        except Abort:
            raise
        except Exception as e:
            logger.error(f"Failed to delete comment: {e}")
            raise Abort(
                f"Failed to delete comment: {e}",
                subject="Mutation Failed",
                log_message=f"GraphQL mutation failed: {e}",
            )


# Global singleton instance
support_ticket_sdk = SupportTicketSDK()
