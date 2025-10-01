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
"""CRUD operations for notebook servers using GraphQL."""

from typing import Any, Dict, List, Optional

import typer
from loguru import logger

from vantage_cli.exceptions import Abort
from vantage_cli.gql_client import create_async_graphql_client
from vantage_cli.jupyterhub_sdk import jupyterhub_sdk
from vantage_cli.sdk.notebook.schema import Notebook


class NotebookSDK:
    """SDK for notebook server operations."""

    async def list_notebooks(
        self,
        ctx: typer.Context,
        cluster: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Notebook]:
        """List all notebook servers.

        Args:
            ctx: Typer context containing settings and profile
            cluster: Optional cluster name filter
            limit: Maximum number of notebooks to return

        Returns:
            List of Notebook objects
        """
        query = """
        query NotebookServers($first: Int) {
            notebookServers(first: $first) {
                edges {
                    node {
                        id
                        name
                        clusterName
                        partition
                        owner
                        serverUrl
                        slurmJobId
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
            # Create async GraphQL client
            profile = getattr(ctx.obj, "profile", "default")
            graphql_client = create_async_graphql_client(ctx.obj.settings, profile)

            # Execute the query
            logger.debug(f"Executing GraphQL query to list notebooks with variables: {variables}")
            response_data = await graphql_client.execute_async(query, variables)

            if not response_data:
                raise Abort(
                    "No response from server",
                    subject="Query Failed",
                    log_message="GraphQL query returned no response",
                )

            notebooks_data = response_data.get("notebookServers", {})
            notebooks_list = [edge["node"] for edge in notebooks_data.get("edges", [])]

            # Apply client-side cluster filter if provided
            if cluster:
                notebooks_list = [n for n in notebooks_list if n.get("clusterName") == cluster]

            # Convert to Notebook objects with proper field mapping
            notebooks = []
            for notebook_dict in notebooks_list:
                # Map camelCase to snake_case for the Pydantic model
                notebook = Notebook(
                    id=notebook_dict.get("id", ""),
                    name=notebook_dict.get("name", ""),
                    cluster_name=notebook_dict.get("clusterName"),
                    partition=notebook_dict.get("partition"),
                    owner=notebook_dict.get("owner"),
                    server_url=notebook_dict.get("serverUrl"),
                    slurm_job_id=notebook_dict.get("slurmJobId"),
                    created_at=notebook_dict.get("createdAt"),
                    updated_at=notebook_dict.get("updatedAt"),
                )
                notebooks.append(notebook)

            logger.debug(f"Successfully retrieved {len(notebooks)} notebooks")
            return notebooks

        except Abort:
            raise
        except Exception as e:
            logger.error(f"Failed to list notebooks: {e}")
            raise Abort(
                f"Failed to list notebook servers: {e}",
                subject="Query Failed",
                log_message=f"GraphQL query failed: {e}",
            )

    async def get_notebook(
        self,
        ctx: typer.Context,
        name: str,
    ) -> Optional[Notebook]:
        """Get a specific notebook server by name.

        Args:
            ctx: Typer context containing settings and profile
            name: Name of the notebook server

        Returns:
            Notebook object if found, None otherwise
        """
        # Since the API doesn't support a singular notebookServer query,
        # we'll use the notebookServers list query and filter by name
        query = """
        query NotebookServers($first: Int) {
            notebookServers(first: $first) {
                edges {
                    node {
                        id
                        name
                        clusterName
                        partition
                        owner
                        serverUrl
                        slurmJobId
                        createdAt
                        updatedAt
                    }
                }
                total
            }
        }
        """

        variables: Dict[str, Any] = {"first": 100}  # Get a reasonable number of notebooks

        try:
            # Create async GraphQL client
            profile = getattr(ctx.obj, "profile", "default")
            graphql_client = create_async_graphql_client(ctx.obj.settings, profile)

            # Execute the query
            logger.debug(f"Executing GraphQL query to get notebook '{name}'")
            response_data = await graphql_client.execute_async(query, variables)

            if not response_data:
                raise Abort(
                    "No response from server",
                    subject="Query Failed",
                    log_message="GraphQL query returned no response",
                )

            notebooks_data = response_data.get("notebookServers", {})
            notebooks_list = [edge["node"] for edge in notebooks_data.get("edges", [])]

            # Filter by name
            matching_notebooks = [n for n in notebooks_list if n.get("name") == name]

            if not matching_notebooks:
                logger.debug(f"Notebook server '{name}' not found")
                return None

            if len(matching_notebooks) > 1:
                logger.warning(
                    f"Multiple notebook servers found with name '{name}', using first match"
                )

            notebook_dict = matching_notebooks[0]

            # Map camelCase to snake_case for the Pydantic model
            notebook = Notebook(
                id=notebook_dict.get("id", ""),
                name=notebook_dict.get("name", ""),
                cluster_name=notebook_dict.get("clusterName"),
                partition=notebook_dict.get("partition"),
                owner=notebook_dict.get("owner"),
                server_url=notebook_dict.get("serverUrl"),
                slurm_job_id=notebook_dict.get("slurmJobId"),
                created_at=notebook_dict.get("createdAt"),
                updated_at=notebook_dict.get("updatedAt"),
            )

            logger.debug(f"Successfully retrieved notebook '{name}'")
            return notebook

        except Abort:
            raise
        except Exception as e:
            logger.error(f"Failed to get notebook '{name}': {e}")
            raise Abort(
                f"Failed to get notebook server: {e}",
                subject="Query Failed",
                log_message=f"GraphQL query failed: {e}",
            )

    async def create_notebook(
        self,
        ctx: typer.Context,
        cluster_name: str,
        username: str,
        server_name: Optional[str] = None,
        server_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new notebook server on a cluster.

        Args:
            ctx: Typer context containing settings and profile
            cluster_name: Name of the cluster to create the notebook on
            username: JupyterHub username for the notebook server
            server_name: Optional named server (creates default server if not provided)
            server_options: Optional server configuration options (e.g., resources, image)

        Returns:
            Dictionary containing server creation details

        Raises:
            Abort: If notebook creation fails
        """
        logger.debug(
            f"Creating notebook server for user '{username}' on cluster '{cluster_name}'"
        )

        try:
            # Use JupyterHub SDK to create the notebook server
            result = await jupyterhub_sdk.create_notebook_server(
                ctx=ctx,
                cluster_name=cluster_name,
                username=username,
                server_name=server_name,
                server_options=server_options,
            )

            logger.info(
                f"Successfully created notebook server for user '{username}' on cluster '{cluster_name}'"
            )
            return result

        except Abort:
            raise
        except Exception as e:
            logger.error(f"Failed to create notebook server: {e}")
            raise Abort(
                f"Failed to create notebook server: {e}",
                subject="Notebook Creation Failed",
                log_message=f"Error creating notebook: {e}",
            )


# Global singleton instance
notebook_sdk = NotebookSDK()
