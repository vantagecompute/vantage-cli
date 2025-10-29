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
"""Base CRUD SDK classes with common patterns extracted from profile and deployment commands."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import typer

from vantage_cli.exceptions import Abort
from vantage_cli.gql_client import create_async_graphql_client
from vantage_cli.render import RenderStepOutput

logger = logging.getLogger(__name__)


class BaseCRUDSDK(ABC):
    """Abstract base class for CRUD SDK operations.

    This class defines the common interface for all CRUD operations
    across different resource types (clusters, profiles, deployments, etc.).
    """

    @abstractmethod
    async def list(self, ctx: typer.Context, **kwargs: Any) -> List[Dict[str, Any]]:
        """List all resources of this type.

        Args:
            ctx: Typer context with settings and console
            **kwargs: Additional filtering/pagination parameters

        Returns:
            List of resource dictionaries
        """
        pass

    @abstractmethod
    async def get(
        self, ctx: typer.Context, resource_id: str, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        """Get a specific resource by ID/name.

        Args:
            ctx: Typer context with settings and console
            resource_id: Unique identifier for the resource
            **kwargs: Additional parameters

        Returns:
            Resource dictionary or None if not found
        """
        pass

    @abstractmethod
    async def create(
        self, ctx: typer.Context, resource_data: Dict[str, Any], **kwargs: Any
    ) -> Dict[str, Any]:
        """Create a new resource.

        Args:
            ctx: Typer context with settings and console
            resource_data: Data for creating the resource
            **kwargs: Additional parameters (force, activate, etc.)

        Returns:
            Created resource dictionary
        """
        pass

    @abstractmethod
    async def update(
        self, ctx: typer.Context, resource_id: str, resource_data: Dict[str, Any], **kwargs: Any
    ) -> Dict[str, Any]:
        """Update an existing resource.

        Args:
            ctx: Typer context with settings and console
            resource_id: Unique identifier for the resource
            resource_data: Updated data for the resource
            **kwargs: Additional parameters

        Returns:
            Updated resource dictionary
        """
        pass

    @abstractmethod
    async def delete(self, ctx: typer.Context, resource_id: str, **kwargs: Any) -> bool:
        """Delete a resource.

        Args:
            ctx: Typer context with settings and console
            resource_id: Unique identifier for the resource
            **kwargs: Additional parameters (force, etc.)

        Returns:
            True if deletion was successful
        """
        pass


class BaseGraphQLResourceSDK(BaseCRUDSDK):
    """Base class for resources that interact with GraphQL APIs.

    This class provides common GraphQL functionality for resources
    like clusters that are managed through the Vantage API.
    """

    def __init__(self, resource_name: str):
        """Initialize GraphQL resource SDK.

        Args:
            resource_name: Name of the resource type (e.g., "cluster", "deployment")
        """
        self.resource_name = resource_name

    async def _execute_graphql_query(
        self, ctx: typer.Context, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a GraphQL query with common error handling.

        Args:
            ctx: Typer context with settings
            query: GraphQL query string
            variables: Query variables

        Returns:
            Query result data

        Raises:
            Abort: If query fails or authentication is invalid
        """
        try:
            profile = getattr(ctx.obj, "profile", "default")
            graphql_client = create_async_graphql_client(ctx.obj.settings, profile)

            response_data = await graphql_client.execute_async(query, variables or {})

            if not response_data:
                raise Abort(
                    f"No data returned from {self.resource_name} query",
                    subject=f"{self.resource_name.title()} Query Failed",
                    log_message="Empty response from GraphQL query",
                )

            return response_data

        except Exception as e:
            logger.error(f"Failed to execute GraphQL query for {self.resource_name}: {str(e)}")
            raise Abort(
                f"Failed to query {self.resource_name}: {str(e)}",
                subject=f"{self.resource_name.title()} Query Failed",
                log_message=f"GraphQL query error: {str(e)}",
            )

    async def list(self, ctx: typer.Context, **kwargs: Any) -> List[Dict[str, Any]]:
        """List resources using GraphQL query.

        This is a default implementation that subclasses can override.
        """
        variables = {"first": kwargs.get("limit", 100)}
        query = self._get_list_query()

        data = await self._execute_graphql_query(ctx, query, variables)

        # Extract items from GraphQL connection structure
        edges = data.get(f"{self.resource_name}s", {}).get("edges", [])
        return [edge["node"] for edge in edges]

    async def get(
        self, ctx: typer.Context, resource_id: str, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        """Get resource by ID using list-and-filter approach.

        This provides a fallback when there's no direct get query.
        Subclasses can override for more efficient direct queries.
        """
        resources = await self.list(ctx, **kwargs)

        # Try to find by various ID fields
        id_fields = kwargs.get("id_fields", ["name", "id", "clientId"])

        for resource in resources:
            for field in id_fields:
                if resource.get(field) == resource_id:
                    return resource

        return None

    @abstractmethod
    def _get_list_query(self) -> str:
        """Get the GraphQL query for listing resources.

        Returns:
            GraphQL query string
        """
        pass


class BaseLocalResourceSDK(BaseCRUDSDK):
    """Base class for resources that are stored locally (config files, etc.).

    This class provides common functionality for resources like profiles
    that are managed through local configuration files.
    """

    def __init__(self, resource_name: str, config_file_path: Optional[str] = None):
        """Initialize local resource SDK.

        Args:
            resource_name: Name of the resource type (e.g., "profile")
            config_file_path: Path to configuration file (optional)
        """
        self.resource_name = resource_name
        self.config_file_path = config_file_path

    def _create_progress_renderer(
        self, ctx: typer.Context, operation_name: str, step_names: List[str], verbose: bool = False
    ) -> RenderStepOutput:
        """Create a progress renderer for operations.

        Args:
            ctx: Typer context
            operation_name: Name of the operation being performed
            step_names: List of step names for progress tracking
            verbose: Whether to enable verbose output

        Returns:
            Configured RenderStepOutput instance
        """
        command_start_time = getattr(ctx.obj, "command_start_time", None) if ctx.obj else None

        return RenderStepOutput(
            console=ctx.obj.console,
            operation_name=operation_name,
            step_names=step_names,
            verbose=verbose,
            command_start_time=command_start_time,
        )

    def _handle_json_output(
        self, json_output: bool, success: bool, data: Dict[str, Any], message: str
    ) -> None:
        """Handle JSON output with consistent structure.

        Args:
            json_output: Whether to output JSON
            success: Whether the operation was successful
            data: Data to include in JSON response
            message: Human-readable message
        """
        if json_output:
            from rich import print_json

            result = {"success": success, "message": message, **data}
            print_json(data=result)

    @abstractmethod
    def _load_all_resources(self) -> Dict[str, Any]:
        """Load all resources from storage.

        Returns:
            Dictionary of all resources keyed by identifier
        """
        pass

    @abstractmethod
    def _save_resource(self, resource_id: str, resource_data: Dict[str, Any]) -> None:
        """Save a resource to storage.

        Args:
            resource_id: Unique identifier for the resource
            resource_data: Resource data to save
        """
        pass

    @abstractmethod
    def _delete_resource(self, resource_id: str) -> None:
        """Delete a resource from storage.

        Args:
            resource_id: Unique identifier for the resource
        """
        pass

    async def list(self, ctx: typer.Context, **kwargs: Any) -> List[Dict[str, Any]]:
        """List all local resources.

        Args:
            ctx: Typer context
            **kwargs: Additional filtering parameters

        Returns:
            List of resource dictionaries
        """
        all_resources = self._load_all_resources()

        # Convert to list format with resource_id included
        resources = []
        for resource_id, resource_data in all_resources.items():
            resource = dict(resource_data)
            resource["id"] = resource_id
            resources.append(resource)

        # Apply filters if provided
        if "filter_func" in kwargs and callable(kwargs["filter_func"]):
            resources = [r for r in resources if kwargs["filter_func"](r)]

        return resources

    async def get(
        self, ctx: typer.Context, resource_id: str, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        """Get a specific local resource.

        Args:
            ctx: Typer context
            resource_id: Resource identifier
            **kwargs: Additional parameters

        Returns:
            Resource dictionary or None if not found
        """
        all_resources = self._load_all_resources()

        if resource_id in all_resources:
            resource = dict(all_resources[resource_id])
            resource["id"] = resource_id
            return resource

        return None


class BaseRestApiResourceSDK(BaseCRUDSDK):
    """Base class for resources that interact with REST APIs.

    This class provides common REST API functionality for resources
    like licenses and jobs that are managed through REST endpoints.
    """

    def __init__(self, resource_name: str, base_path: str, endpoint_path: str):
        """Initialize REST API resource SDK.

        Args:
            resource_name: Name of the resource type (e.g., "license_server", "job_script")
            base_path: Base path for the API (e.g., "/lm", "/jobbergate")
            endpoint_path: Endpoint path for this resource (e.g., "/license_servers", "/job-scripts")
        """
        self.resource_name = resource_name
        self.base_path = base_path
        self.endpoint_path = endpoint_path

    def _get_rest_client(self, ctx: typer.Context):
        """Get or create REST client from context.

        Args:
            ctx: Typer context

        Returns:
            VantageRestApiClient instance

        Raises:
            RuntimeError: If rest_client not attached to context
        """
        if not hasattr(ctx.obj, "rest_client") or ctx.obj.rest_client is None:
            raise RuntimeError(
                f"REST client not attached. Ensure @attach_vantage_rest_client(base_path='{self.base_path}') "
                f"is applied to the command function."
            )
        return ctx.obj.rest_client

    async def list(self, ctx: typer.Context, **kwargs: Any) -> List[Dict[str, Any]]:
        """List all resources via REST API.

        Args:
            ctx: Typer context with rest_client attached
            **kwargs: Query parameters (search, sort, limit, offset, etc.)

        Returns:
            List of resource dictionaries
        """
        rest_client = self._get_rest_client(ctx)

        # Build query parameters
        params = {}
        for key in [
            "search",
            "sort",
            "sort_field",
            "sort_ascending",
            "limit",
            "offset",
            "page",
            "perPage",
        ]:
            if key in kwargs and kwargs[key] is not None:
                params[key] = kwargs[key]

        response = await rest_client.get(self.endpoint_path, params=params if params else None)

        # Handle different response formats
        if isinstance(response, list):
            return response
        elif isinstance(response, dict):
            # Check for common pagination wrappers
            if "items" in response:
                return response["items"]
            elif "data" in response:
                return response["data"]
            elif "results" in response:
                return response["results"]
            # Return as single-item list if it looks like a single resource
            return [response]

        return []

    async def get(
        self, ctx: typer.Context, resource_id: str, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        """Get a specific resource by ID via REST API.

        Args:
            ctx: Typer context with rest_client attached
            resource_id: Unique identifier for the resource
            **kwargs: Additional parameters

        Returns:
            Resource dictionary or None if not found
        """
        rest_client = self._get_rest_client(ctx)

        try:
            response = await rest_client.get(f"{self.endpoint_path}/{resource_id}")
            return response if isinstance(response, dict) else None
        except Exception as e:
            logger.debug(f"Failed to get {self.resource_name} {resource_id}: {e}")
            return None

    async def create(
        self, ctx: typer.Context, resource_data: Dict[str, Any], **kwargs: Any
    ) -> Dict[str, Any]:
        """Create a new resource via REST API.

        Args:
            ctx: Typer context with rest_client attached
            resource_data: Data for creating the resource
            **kwargs: Additional parameters

        Returns:
            Created resource dictionary
        """
        rest_client = self._get_rest_client(ctx)

        response = await rest_client.post(self.endpoint_path, json=resource_data)

        if isinstance(response, dict):
            return response

        raise ValueError(f"Unexpected response format from create {self.resource_name}")

    async def update(
        self, ctx: typer.Context, resource_id: str, resource_data: Dict[str, Any], **kwargs: Any
    ) -> Dict[str, Any]:
        """Update an existing resource via REST API.

        Args:
            ctx: Typer context with rest_client attached
            resource_id: Unique identifier for the resource
            resource_data: Updated data for the resource
            **kwargs: Additional parameters

        Returns:
            Updated resource dictionary
        """
        rest_client = self._get_rest_client(ctx)

        response = await rest_client.put(f"{self.endpoint_path}/{resource_id}", json=resource_data)

        if isinstance(response, dict):
            return response

        raise ValueError(f"Unexpected response format from update {self.resource_name}")

    async def delete(self, ctx: typer.Context, resource_id: str, **kwargs: Any) -> bool:
        """Delete a resource via REST API.

        Args:
            ctx: Typer context with rest_client attached
            resource_id: Unique identifier for the resource
            **kwargs: Additional parameters

        Returns:
            True if deletion was successful
        """
        rest_client = self._get_rest_client(ctx)

        try:
            await rest_client.delete(f"{self.endpoint_path}/{resource_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {self.resource_name} {resource_id}: {e}")
            return False
