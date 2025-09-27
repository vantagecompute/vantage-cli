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

import logging
import re
from typing import Any, Dict, List, Optional

import typer

from vantage_cli.exceptions import Abort
from vantage_cli.gql_client import GraphQLError, create_async_graphql_client
from vantage_cli.jupyterhub_sdk import jupyterhub_sdk
from vantage_cli.sdk.notebook.schema import Notebook

logger = logging.getLogger(__name__)


_MEMORY_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+)?)([kKmMgGtT])?\s*$")


def _parse_memory_option(memory_value: Any) -> tuple[float, Optional[str]]:
    """Parse a memory specification (e.g. '4G') into value/unit components."""
    if memory_value is None:
        raise Abort(
            "Memory specification cannot be None when provided.",
            subject="Invalid Memory Specification",
            log_message="Received None for memory option",
        )

    if isinstance(memory_value, (int, float)):
        return float(memory_value), None

    if not isinstance(memory_value, str):
        raise Abort(
            f"Unsupported memory specification type: {type(memory_value)}",
            subject="Invalid Memory Specification",
            log_message=f"Unsupported memory option type: {type(memory_value)}",
        )

    match = _MEMORY_PATTERN.match(memory_value)
    if not match:
        raise Abort(
            f"Invalid memory specification '{memory_value}'. Use formats like 4G or 4096M.",
            subject="Invalid Memory Specification",
            log_message=f"Unable to parse memory option: {memory_value}",
        )

    numeric_value = float(match.group(1))
    unit = match.group(2).upper() if match.group(2) else None
    return numeric_value, unit


def _notebook_to_result(
    notebook: Notebook,
    username: str,
    *,
    status: str,
    message: str,
) -> Dict[str, Any]:
    """Convert a Notebook model into the SDK response payload shape."""
    return {
        "cluster_name": notebook.cluster_name,
        "partition": notebook.partition,
        "server_name": notebook.name,
        "server_url": notebook.server_url,
        "slurm_job_id": notebook.slurm_job_id,
        "owner": notebook.owner,
        "status": status,
        "message": message,
        "username": username,
    }


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
            notebooks: List[Notebook] = []
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
        """Create (or reuse) a notebook server on a cluster via GraphQL."""
        logger.debug(
            "Creating notebook server via GraphQL for user '%s' on cluster '%s'",
            username,
            cluster_name,
        )

        if not server_name:
            raise Abort(
                "Notebook creation requires a server name. Supply one with --name.",
                subject="Server Name Required",
                log_message="Missing server_name for notebook creation",
            )

        partition_name: Optional[str] = None
        if server_options:
            partition_name = server_options.get("partition")

        if not partition_name:
            raise Abort(
                "Notebook creation requires a partition. Provide one with --partition.",
                subject="Partition Required",
                log_message="Missing partition for notebook creation",
            )

        mutation = """
        mutation CreateJupyterServer($input: CreateNotebookInput!) {
            createJupyterServer(createNotebookInput: $input) {
                __typename
                ... on NotebookServer {
                    name
                    clusterName
                    partition
                    owner
                    serverUrl
                    slurmJobId
                }
                ... on NotebookServerAlreadyExists {
                    message
                }
                ... on ClusterNotFound {
                    message
                }
                ... on PartitionNotFound {
                    message
                }
            }
        }
        """

        input_payload: Dict[str, Any] = {
            "name": server_name,
            "clusterName": cluster_name,
            "partitionName": partition_name,
        }

        if server_options:
            if (cpu_cores := server_options.get("cpu_cores")) is not None:
                input_payload["cpuCores"] = int(cpu_cores)

            if (gpus := server_options.get("gpus")) is not None:
                input_payload["gpus"] = int(gpus)

            if node_name := server_options.get("node"):
                input_payload["nodeName"] = node_name

            if (memory := server_options.get("memory")) is not None:
                memory_value, memory_unit = _parse_memory_option(memory)
                input_payload["memory"] = memory_value
                if memory_unit:
                    input_payload["memoryUnit"] = memory_unit

        profile = getattr(ctx.obj, "profile", "default")
        graphql_client = create_async_graphql_client(ctx.obj.settings, profile)

        variables = {"input": input_payload}
        logger.debug("Executing createJupyterServer mutation with input: %s", variables)

        try:
            response_data = await graphql_client.execute_async(mutation, variables)
        except Abort:
            raise
        except GraphQLError as exc:
            error_message = str(exc)
            logger.error(f"GraphQL notebook creation failed: {error_message}")

            transport_indicators = ("transport error", "timeout", "connection failed")
            if any(indicator in error_message.lower() for indicator in transport_indicators):
                logger.warning(
                    "GraphQL transport error encountered; attempting to fetch existing notebook '%s'",
                    server_name,
                )
                try:
                    existing_notebook = await self.get_notebook(ctx, server_name)
                except Abort:
                    existing_notebook = None

                if existing_notebook:
                    return _notebook_to_result(
                        existing_notebook,
                        username,
                        status="pending",
                        message=(
                            "Notebook creation request timed out while contacting the API. "
                            "Returning the latest record; use 'vantage notebook list' to verify status."
                        ),
                    )

                logger.info(
                    "GraphQL transport error could not be recovered; falling back to JupyterHub REST API",
                )

                try:
                    rest_response = await jupyterhub_sdk.create_notebook_server(
                        ctx=ctx,
                        cluster_name=cluster_name,
                        username=username,
                        server_name=server_name,
                        server_options=server_options,
                    )
                except Abort:
                    raise
                except Exception as rest_exc:  # pragma: no cover - defensive guard
                    logger.error(
                        "JupyterHub REST fallback failed: %s",
                        rest_exc,
                    )
                else:
                    fallback_message = (
                        rest_response.get(
                            "message",
                            "Notebook server creation requested",
                        )
                        + " (fallback via JupyterHub API after GraphQL transport error)"
                    )

                    return {
                        "cluster_name": rest_response.get("cluster_name", cluster_name),
                        "partition": partition_name,
                        "server_name": rest_response.get("server_name", server_name),
                        "server_url": rest_response.get("server_url"),
                        "slurm_job_id": rest_response.get("slurm_job_id"),
                        "owner": rest_response.get("owner"),
                        "status": rest_response.get("status", "pending"),
                        "message": fallback_message,
                        "username": rest_response.get("username", username),
                    }

            raise Abort(
                f"Failed to create notebook server: {error_message}",
                subject="Notebook Creation Failed",
                log_message=f"GraphQL mutation error: {error_message}",
            )
        except Exception as exc:
            logger.error(f"GraphQL notebook creation failed: {exc}")
            raise Abort(
                f"Failed to create notebook server: {exc}",
                subject="Notebook Creation Failed",
                log_message=f"GraphQL mutation error: {exc}",
            )

        if not response_data:
            raise Abort(
                "No response received from notebook creation API.",
                subject="Notebook Creation Failed",
                log_message="Empty response from createJupyterServer mutation",
            )

        mutation_result = response_data.get("createJupyterServer")
        if not mutation_result:
            raise Abort(
                "Unexpected response structure while creating notebook server.",
                subject="Notebook Creation Failed",
                log_message="createJupyterServer field missing from GraphQL response",
            )

        typename = mutation_result.get("__typename")
        if typename == "NotebookServerAlreadyExists":
            logger.info(
                "Notebook server '%s' already registered; attempting to fetch existing record",
                server_name,
            )

            existing_notebook = await self.get_notebook(ctx, server_name)
            if existing_notebook:
                return _notebook_to_result(
                    existing_notebook,
                    username,
                    status="exists",
                    message="Notebook server already exists; returning existing record.",
                )

            error_message = (
                "Notebook server already exists according to the API, but no record could be fetched. "
                "Use 'vantage notebook list' to inspect existing notebooks."
            )
            logger.error(error_message)
            raise Abort(
                error_message,
                subject="Notebook Creation Failed",
                log_message="createJupyterServer reported NotebookServerAlreadyExists but record missing",
            )

        if typename and typename != "NotebookServer":
            error_message = mutation_result.get(
                "message", "Notebook server creation was rejected by the API."
            )
            logger.error(f"Notebook creation returned {typename}: {error_message}")
            raise Abort(
                error_message,
                subject="Notebook Creation Failed",
                log_message=f"GraphQL createJupyterServer returned {typename}",
            )

        notebook_info = mutation_result
        result_payload: Dict[str, Any] = {
            "cluster_name": notebook_info.get("clusterName"),
            "partition": notebook_info.get("partition"),
            "server_name": notebook_info.get("name"),
            "server_url": notebook_info.get("serverUrl"),
            "slurm_job_id": notebook_info.get("slurmJobId"),
            "owner": notebook_info.get("owner"),
            "status": "created",
            "message": "Notebook server creation requested",
            "username": username,
        }

        logger.info(
            "Successfully requested notebook server '%s' via GraphQL",
            result_payload["server_name"],
        )

        return result_payload


# Global singleton instance
notebook_sdk = NotebookSDK()
