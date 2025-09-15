"""Tests for the noteboks servers GraphQL API."""

import random
from unittest import mock

import httpx
import pytest

from api.graphql_app import schema
from api.graphql_app.types import Context, MemoryUnit
from api.settings import SETTINGS
from tests.conftest import SeededData


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "stage, status_code, expected_available, expected_domain",
    [
        ("production", 200, True, "https://client123.vantagecompute.ai"),
        ("production", 503, False, "https://client123.vantagecompute.ai"),
        ("staging", 200, True, "https://client123.staging.vantagecompute.ai"),
        ("dev", 404, False, "https://client123.dev.vantagecompute.ai"),
    ],
)
@mock.patch("api.graphql_app.resolvers.notebooks.httpx.get")
async def test_get_jupyterhub_status(
    mocked_httpx_get,
    stage,
    status_code,
    expected_available,
    expected_domain,
    enforce_strawberry_context_authentication: None,
):
    """Test the availability status of JupyterHub under various deployment stages and HTTP responses."""
    client_id = "client123"
    mocked_httpx_get.return_value.status_code = status_code

    context = Context()
    query = """
        query getJupyterhubStatus($clientId: String!) {
            jupyterhubStatus(clientId: $clientId) {
                available
            }
        }
    """
    variables = {"clientId": client_id}

    with mock.patch.object(SETTINGS, "STAGE", stage), mock.patch.object(
        SETTINGS, "APP_DOMAIN", "vantagecompute.ai"
    ):
        response = await schema.execute(query, variable_values=variables, context_value=context)

        assert response.errors is None
        assert response.data.get("jupyterhubStatus").get("available") is expected_available
        mocked_httpx_get.assert_called_once_with(f"{expected_domain}/hub/api/", timeout=5.0)


@pytest.mark.asyncio
async def test_check_progress__notebook_not_found(
    enforce_strawberry_context_authentication: None,
):
    """Test that querying the progress of a nonexistent notebook server returns NotebookServerNotFound."""
    notebook_name = "not-found"
    context = Context()
    query = """
        query notebookStatus($notebookName: String!) {
            notebookServerProgress(notebookServerName: $notebookName) {
                __typename
                ... on NotebookServerNotFound {
                    message
                }
                ... on NotebookServerProgress {
                    ready
                }
            }
        }
    """
    variables = {"notebookName": notebook_name}

    response = await schema.execute(query, variable_values=variables, context_value=context)

    assert response.errors is None
    assert response.data.get("notebookServerProgress").get("__typename") == "NotebookServerNotFound"
    assert (
        response.data.get("notebookServerProgress").get("message")
        == f"Notebook Server {notebook_name} not found."
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("ready_flag", [True, False])
@mock.patch("api.graphql_app.resolvers.notebooks.httpx.get")
async def test_check_progress__notebook_found(
    mock_httpx_get,
    ready_flag,
    enforce_strawberry_context_authentication: None,
    seed_database: SeededData,
):
    """Test that querying the progress of an existing notebook server returns the correct readiness status."""
    notebook_name = seed_database.notebook_server.name

    http_reponse = mock.MagicMock()
    http_reponse.json = mock.MagicMock()
    http_reponse.json.return_value = {"servers": {f"{notebook_name}": {"ready": ready_flag}}}
    mock_httpx_get.return_value = http_reponse

    context = Context()
    query = """
        query notebookStatus($notebookName: String!) {
            notebookServerProgress(notebookServerName: $notebookName) {
                __typename
                ... on NotebookServerNotFound {
                    message
                }
                ... on NotebookServerProgress {
                    ready
                }
            }
        }
    """
    variables = {"notebookName": notebook_name}

    response = await schema.execute(query, variable_values=variables, context_value=context)
    assert response.errors is None
    assert response.data.get("notebookServerProgress").get("__typename") == "NotebookServerProgress"
    assert response.data.get("notebookServerProgress").get("ready") == ready_flag


@pytest.mark.asyncio
async def test_create_notebook__already_exists(
    enforce_strawberry_context_authentication: None,
    seed_database,
):
    """Test that attempting to create a notebook with a name that already exists."""
    context = Context()
    query = """
        mutation CreateNotebookServer($input: CreateNotebookInput!) {
            createJupyterServer(createNotebookInput: $input) {
                __typename
                ... on NotebookServerAlreadyExists {
                    message
                }
                ... on NotebookServer {
                    name
                }
                ... on ClusterNotFound {
                    message
                }
                ... on PartitionNotFound {
                    message
                }
                ... on NotebookServer {
                    name
                    owner
                    clusterName
                    partition
                    serverUrl
                }
            }
        }
    """
    variables = {
        "input": {
            "name": seed_database.notebook_server.name,
            "clusterName": seed_database.cluster.name,
            "partitionName": seed_database.notebook_server.partition,
        }
    }

    response = await schema.execute(query, variable_values=variables, context_value=context)
    assert response.errors is None
    assert response.data.get("createJupyterServer").get("__typename") == "NotebookServerAlreadyExists"
    assert (
        response.data.get("createJupyterServer").get("message")
        == "Notebook Server already exists with the given name."
    )


@pytest.mark.asyncio
async def test_create_notebook__cluster_not_found(
    enforce_strawberry_context_authentication: None,
):
    """Test that creating a notebook with a nonexistent cluster returns ClusterNotFound."""
    context = Context()
    query = """
        mutation CreateNotebookServer($input: CreateNotebookInput!) {
            createJupyterServer(createNotebookInput: $input) {
                __typename
                ... on NotebookServerAlreadyExists {
                    message
                }
                ... on NotebookServer {
                    name
                }
                ... on ClusterNotFound {
                    message
                }
                ... on PartitionNotFound {
                    message
                }
                ... on NotebookServer {
                    name
                    owner
                    clusterName
                    partition
                    serverUrl
                }
            }
        }
    """
    variables = {
        "input": {
            "name": "new-notebook-not-found",
            "clusterName": "non-existent-cluster",
            "partitionName": "compute",
        }
    }

    response = await schema.execute(query, variable_values=variables, context_value=context)

    assert response.errors is None
    assert response.data.get("createJupyterServer").get("__typename") == "ClusterNotFound"
    assert response.data.get("createJupyterServer").get("message") == "Cluster could not be found."


@pytest.mark.asyncio
async def test_create_notebook__partition_not_found(
    enforce_strawberry_context_authentication: None,
    seed_database,
):
    """Test that creating a notebook with an invalid partition name returns PartitionNotFound."""
    context = Context()
    query = """
        mutation CreateNotebookServer($input: CreateNotebookInput!) {
            createJupyterServer(createNotebookInput: $input) {
                __typename
                ... on NotebookServerAlreadyExists {
                    message
                }
                ... on NotebookServer {
                    name
                }
                ... on ClusterNotFound {
                    message
                }
                ... on PartitionNotFound {
                    message
                }
                ... on NotebookServer {
                    name
                    owner
                    clusterName
                    partition
                    serverUrl
                }
            }
        }
    """
    variables = {
        "input": {
            "name": "new-notebook",
            "clusterName": seed_database.cluster.name,
            "partitionName": "invalid-partition",
        }
    }

    response = await schema.execute(query, variable_values=variables, context_value=context)
    assert response.errors is None
    assert response.data.get("createJupyterServer").get("__typename") == "PartitionNotFound"
    assert response.data.get("createJupyterServer").get("message") == "Cluster Partition not be found."


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.notebooks.httpx.post")
@mock.patch("api.graphql_app.resolvers.notebooks.httpx.get")
async def test_create_notebook__success_without_specs(
    mock_httpx_get,
    mock_httpx_post,
    enforce_strawberry_context_authentication: None,
    seed_database,
):
    """Test successful creation of a notebook server.

    Test when a server is created with success including interaction
    with the JupyterHub API and database insertion.
    """
    stage = "dev"
    domain = "vantagecompute.ai"
    server_url = f"https://{seed_database.cluster.client_id}.{stage}.{domain}"

    context = Context()
    query = """
        mutation CreateNotebookServer($input: CreateNotebookInput!) {
            createJupyterServer(createNotebookInput: $input) {
                __typename
                ... on NotebookServerAlreadyExists {
                    message
                }
                ... on NotebookServer {
                    name
                }
                ... on ClusterNotFound {
                    message
                }
                ... on PartitionNotFound {
                    message
                }
                ... on NotebookServer {
                    name
                    owner
                    clusterName
                    partition
                    serverUrl
                    slurmJobId
                }
            }
        }
    """
    notebook_name = "created-notebook"
    variables = {
        "input": {
            "name": notebook_name,
            "clusterName": seed_database.cluster.name,
            "partitionName": seed_database.partition.name,
        }
    }

    http_reponse_post = mock.MagicMock()
    http_reponse_post.json = mock.MagicMock(return_value={})
    mock_httpx_post.return_value.status_code = 201
    mock_httpx_post.return_value = http_reponse_post

    slurm_job_id = random.randint(1000000, 9999999)
    http_reponse_get = mock.MagicMock()
    http_reponse_get.json = mock.MagicMock(
        return_value={"servers": {notebook_name: {"state": {"job_id": str(slurm_job_id)}}}}
    )
    mock_httpx_get.return_value.status_code = 200
    mock_httpx_get.return_value = http_reponse_get

    with mock.patch.object(SETTINGS, "STAGE", stage), mock.patch.object(SETTINGS, "APP_DOMAIN", domain):
        response = await schema.execute(query, variable_values=variables, context_value=context)

    assert response.errors is None
    assert response.data.get("createJupyterServer").get("__typename") == "NotebookServer"
    assert response.data.get("createJupyterServer").get("name") == notebook_name
    assert response.data.get("createJupyterServer").get("clusterName") == seed_database.cluster.name
    assert response.data.get("createJupyterServer").get("partition") == seed_database.partition.name
    assert response.data.get("createJupyterServer").get("serverUrl") == server_url
    assert response.data.get("createJupyterServer").get("slurmJobId") == slurm_job_id

    mock_httpx_post.assert_called_once()
    mock_httpx_get.assert_called_once()


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.notebooks.httpx.post")
@mock.patch("api.graphql_app.resolvers.notebooks.httpx.get")
async def test_create_notebook__success_with_specs(
    mock_httpx_get,
    mock_httpx_post,
    enforce_strawberry_context_authentication: None,
    seed_database,
):
    """Test successful creation of a notebook server.

    Test when a server is created with success including interaction
    with the JupyterHub API and database insertion.
    """
    stage = "dev"
    domain = "vantagecompute.ai"
    server_url = f"https://{seed_database.cluster.client_id}.{stage}.{domain}"

    context = Context()
    query = """
        mutation CreateNotebookServer($input: CreateNotebookInput!) {
            createJupyterServer(createNotebookInput: $input) {
                __typename
                ... on NotebookServerAlreadyExists {
                    message
                }
                ... on NotebookServer {
                    name
                }
                ... on ClusterNotFound {
                    message
                }
                ... on PartitionNotFound {
                    message
                }
                ... on NotebookServer {
                    name
                    owner
                    clusterName
                    partition
                    serverUrl
                    slurmJobId
                }
            }
        }
    """
    cpus = random.randint(1, 50)
    gpus = random.randint(1, 50)
    memory = random.uniform(1, 1024)
    memory_unit = random.choice(list(MemoryUnit))

    notebook_name = "created-notebook"
    variables = {
        "input": {
            "name": notebook_name,
            "clusterName": seed_database.cluster.name,
            "partitionName": seed_database.partition.name,
            "cpuCores": cpus,
            "memory": memory,
            "memoryUnit": memory_unit.value,
            "gpus": gpus,
        }
    }

    http_reponse_post = mock.MagicMock()
    http_reponse_post.json = mock.MagicMock(return_value={})
    mock_httpx_post.return_value.status_code = 201
    mock_httpx_post.return_value = http_reponse_post

    slurm_job_id = random.randint(1000000, 9999999)
    http_reponse_get = mock.MagicMock()
    http_reponse_get.json = mock.MagicMock(
        return_value={"servers": {notebook_name: {"state": {"job_id": str(slurm_job_id)}}}}
    )
    mock_httpx_get.return_value.status_code = 200
    mock_httpx_get.return_value = http_reponse_get

    with mock.patch.object(SETTINGS, "STAGE", stage), mock.patch.object(SETTINGS, "APP_DOMAIN", domain):
        response = await schema.execute(query, variable_values=variables, context_value=context)

    assert response.errors is None
    assert response.data.get("createJupyterServer").get("__typename") == "NotebookServer"
    assert response.data.get("createJupyterServer").get("name") == notebook_name
    assert response.data.get("createJupyterServer").get("clusterName") == seed_database.cluster.name
    assert response.data.get("createJupyterServer").get("partition") == seed_database.partition.name
    assert response.data.get("createJupyterServer").get("serverUrl") == server_url
    assert response.data.get("createJupyterServer").get("slurmJobId") == slurm_job_id

    headers = {
        "Authorization": f"token {seed_database.cluster.creation_parameters.get('jupyterhub_token')}",
        "Content-Type": "application/json",
    }
    request_payload = {
        "name": "ubuntu",
        "server_name": notebook_name,
        "partition": seed_database.partition.name,
        "gres": f"gpu:{str(gpus)}",
        "memory": f"{int(memory)}{memory_unit.value}",
        "nprocs": str(cpus),
    }
    api_url = f"{server_url}/hub/api/users/ubuntu/servers/{notebook_name}"

    mock_httpx_post.assert_called_once_with(
        api_url, headers=headers, json=request_payload, timeout=httpx.Timeout(20)
    )
    mock_httpx_get.assert_called_once()


@pytest.mark.asyncio
async def test_delete_notebook__not_found(
    enforce_strawberry_context_authentication: None,
):
    """Test that deleting a nonexistent notebook server returns NotebookServerNotFound."""
    notebook_name = "non-existent-notebook"
    context = Context()
    query = """
        mutation DeleteNotebook($notebookServerName: String!) {
            deleteJupyterServer(notebookServerName: $notebookServerName) {
                __typename
                ... on NotebookServerNotFound {
                    message
                }
                ... on NotebookServerDeleted {
                    message
                }
            }
        }
    """
    variables = {"notebookServerName": notebook_name}

    response = await schema.execute(query, variable_values=variables, context_value=context)

    assert response.errors is None
    assert response.data.get("deleteJupyterServer").get("__typename") == "NotebookServerNotFound"
    assert (
        response.data.get("deleteJupyterServer").get("message")
        == f"Notebook Server {notebook_name} not found."
    )


@pytest.mark.asyncio
async def test_delete_notebook__unauthorized_owner(
    enforce_strawberry_context_authentication: None,
    seed_database,
):
    """Test that deleting a notebook server owned by another user return an error."""
    context = Context()
    context.token_data.email = "intruder@example.com"
    query = """
        mutation DeleteNotebook($notebookServerName: String!) {
            deleteJupyterServer(notebookServerName: $notebookServerName) {
                __typename
                ... on NotebookServerNotFound {
                    message
                }
            }
        }
    """
    variables = {"notebookServerName": seed_database.notebook_server.name}

    response = await schema.execute(query, variable_values=variables, context_value=context)

    assert response.errors is None
    assert response.data.get("deleteJupyterServer").get("__typename") == "NotebookServerNotFound"
    assert (
        response.data.get("deleteJupyterServer").get("message")
        == f"Notebook Server {seed_database.notebook_server.name} not found."
    )


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.notebooks.httpx.delete")
async def test_delete_notebook__admin_user(
    mock_httpx_delete,
    enforce_strawberry_context_authentication: None,
    seed_database,
):
    """Test that deleting a notebook server owned by another user return an error."""
    context = Context()
    context.token_data.email = "admin@example.com"
    context.token_data.permissions.append("notebook:admin")
    query = """
        mutation DeleteNotebook($notebookServerName: String!) {
            deleteJupyterServer(notebookServerName: $notebookServerName) {
                __typename
                ... on NotebookServerDeleted {
                    message
                }
            }
        }
    """
    variables = {"notebookServerName": seed_database.notebook_server.name}

    http_response = mock.MagicMock()
    http_response.status_code = 204
    mock_httpx_delete.return_value = http_response

    response = await schema.execute(query, variable_values=variables, context_value=context)

    assert response.errors is None
    assert response.data["deleteJupyterServer"]["__typename"] == "NotebookServerDeleted"
    assert response.data.get("deleteJupyterServer").get("message") == "Notebook Server has been deleted."


@pytest.mark.asyncio
@mock.patch("api.graphql_app.resolvers.notebooks.httpx.delete")
async def test_delete_notebook__success(
    mock_httpx_delete,
    enforce_strawberry_context_authentication: None,
    seed_database,
):
    """Test successful deletion of a notebook server."""
    context = Context()
    query = """
        mutation DeleteNotebook($notebookServerName: String!) {
            deleteJupyterServer(notebookServerName: $notebookServerName) {
                __typename
                ... on NotebookServerDeleted {
                    message
                }
            }
        }
    """
    variables = {"notebookServerName": seed_database.notebook_server.name}

    http_response = mock.MagicMock()
    http_response.status_code = 204
    mock_httpx_delete.return_value = http_response

    response = await schema.execute(query, variable_values=variables, context_value=context)

    assert response.errors is None
    assert response.data["deleteJupyterServer"]["__typename"] == "NotebookServerDeleted"
    assert response.data.get("deleteJupyterServer").get("message") == "Notebook Server has been deleted."

    mock_httpx_delete.assert_called_once()
