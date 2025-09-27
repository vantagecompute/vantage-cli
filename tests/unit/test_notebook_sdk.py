"""Unit tests for the notebook SDK GraphQL integration."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
import typer

import vantage_cli.sdk.notebook.crud as notebook_crud
from vantage_cli.exceptions import Abort
from vantage_cli.gql_client import GraphQLError
from vantage_cli.sdk.notebook.crud import NotebookSDK
from vantage_cli.sdk.notebook.schema import Notebook


@pytest.mark.asyncio
async def test_notebook_sdk_create_notebook_calls_graphql(monkeypatch: pytest.MonkeyPatch):
    """The SDK should invoke the GraphQL mutation with transformed options."""
    ctx = Mock(spec=typer.Context)
    ctx.obj = SimpleNamespace(profile="default", settings=Mock())

    mock_client = Mock()
    mock_client.execute_async = AsyncMock(
        return_value={
            "createJupyterServer": {
                "__typename": "NotebookServer",
                "name": "nb1",
                "clusterName": "cluster-a",
                "partition": "compute",
                "owner": "owner@example.com",
                "serverUrl": "https://cluster-a.example",
                "slurmJobId": 42,
            }
        }
    )

    monkeypatch.setattr(
        "vantage_cli.sdk.notebook.crud.create_async_graphql_client",
        Mock(return_value=mock_client),
    )

    sdk = NotebookSDK()
    result = await sdk.create_notebook(
        ctx=ctx,
        cluster_name="cluster-a",
        username="user",
        server_name="nb1",
        server_options={
            "partition": "compute",
            "cpu_cores": 2,
            "memory": "4G",
            "gpus": 1,
            "node": "node-1",
        },
    )

    mock_client.execute_async.assert_awaited_once()
    _, variables = mock_client.execute_async.await_args.args
    assert variables == {
        "input": {
            "name": "nb1",
            "clusterName": "cluster-a",
            "partitionName": "compute",
            "cpuCores": 2,
            "gpus": 1,
            "nodeName": "node-1",
            "memory": 4.0,
            "memoryUnit": "G",
        }
    }

    assert result["cluster_name"] == "cluster-a"
    assert result["server_name"] == "nb1"
    assert result["status"] == "created"
    assert result["partition"] == "compute"
    assert result["server_url"] == "https://cluster-a.example"
    assert result["slurm_job_id"] == 42


@pytest.mark.asyncio
async def test_notebook_sdk_create_notebook_returns_existing_when_duplicate(
    monkeypatch: pytest.MonkeyPatch,
):
    """Duplicate notebook creation should return the existing record instead of failing."""
    ctx = Mock(spec=typer.Context)
    ctx.obj = SimpleNamespace(profile="default", settings=Mock())

    mock_client = Mock()
    mock_client.execute_async = AsyncMock(
        return_value={
            "createJupyterServer": {
                "__typename": "NotebookServerAlreadyExists",
                "message": "Notebook already exists",
            }
        }
    )

    monkeypatch.setattr(
        "vantage_cli.sdk.notebook.crud.create_async_graphql_client",
        Mock(return_value=mock_client),
    )

    mock_get = AsyncMock()
    mock_get.return_value = Notebook(
        id="1",
        name="nb1",
        cluster_name="cluster-a",
        partition="compute",
        owner="owner@example.com",
        server_url="https://cluster-a.example",
        slurm_job_id="42",
    )

    monkeypatch.setattr(NotebookSDK, "get_notebook", mock_get)

    sdk = NotebookSDK()

    result = await sdk.create_notebook(
        ctx=ctx,
        cluster_name="cluster-a",
        username="user",
        server_name="nb1",
        server_options={"partition": "compute"},
    )

    assert result["status"] == "exists"
    assert result["server_name"] == "nb1"
    assert result["cluster_name"] == "cluster-a"
    assert "already exists" in result["message"]


@pytest.mark.asyncio
async def test_notebook_sdk_create_notebook_handles_other_union_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    """Non-success union responses should still raise Abort errors."""
    ctx = Mock(spec=typer.Context)
    ctx.obj = SimpleNamespace(profile="default", settings=Mock())

    mock_client = Mock()
    mock_client.execute_async = AsyncMock(
        return_value={
            "createJupyterServer": {
                "__typename": "PartitionNotFound",
                "message": "Partition missing",
            }
        }
    )

    monkeypatch.setattr(
        "vantage_cli.sdk.notebook.crud.create_async_graphql_client",
        Mock(return_value=mock_client),
    )

    sdk = NotebookSDK()

    with pytest.raises(Abort) as excinfo:
        await sdk.create_notebook(
            ctx=ctx,
            cluster_name="cluster-a",
            username="user",
            server_name="nb1",
            server_options={"partition": "compute"},
        )

    assert "Partition missing" in str(excinfo.value)


@pytest.mark.asyncio
async def test_notebook_sdk_create_notebook_falls_back_on_transport_error(
    monkeypatch: pytest.MonkeyPatch,
):
    """Transport failures should attempt to return an existing notebook record."""
    ctx = Mock(spec=typer.Context)
    ctx.obj = SimpleNamespace(profile="default", settings=Mock())

    mock_client = Mock()
    mock_client.execute_async = AsyncMock(
        side_effect=GraphQLError("Transport error during CreateJupyterServer: TimeoutError")
    )

    monkeypatch.setattr(
        "vantage_cli.sdk.notebook.crud.create_async_graphql_client",
        Mock(return_value=mock_client),
    )

    existing_notebook = Notebook(
        id="1",
        name="nb1",
        cluster_name="cluster-a",
        partition="compute",
        owner="owner@example.com",
        server_url="https://cluster-a.example",
        slurm_job_id="42",
    )

    monkeypatch.setattr(NotebookSDK, "get_notebook", AsyncMock(return_value=existing_notebook))

    sdk = NotebookSDK()

    result = await sdk.create_notebook(
        ctx=ctx,
        cluster_name="cluster-a",
        username="user",
        server_name="nb1",
        server_options={"partition": "compute"},
    )

    assert result["status"] == "pending"
    assert "timed out" in result["message"].lower()


@pytest.mark.asyncio
async def test_notebook_sdk_create_notebook_uses_jupyterhub_fallback_when_needed(
    monkeypatch: pytest.MonkeyPatch,
):
    """When no existing notebook is found, fall back to the JupyterHub REST API."""
    ctx = Mock(spec=typer.Context)
    ctx.obj = SimpleNamespace(profile="default", settings=Mock())

    mock_client = Mock()
    mock_client.execute_async = AsyncMock(
        side_effect=GraphQLError("Transport error during CreateJupyterServer: TimeoutError")
    )

    monkeypatch.setattr(
        "vantage_cli.sdk.notebook.crud.create_async_graphql_client",
        Mock(return_value=mock_client),
    )

    monkeypatch.setattr(NotebookSDK, "get_notebook", AsyncMock(return_value=None))

    jhub_result = {
        "cluster_name": "cluster-a",
        "username": "user",
        "server_name": "nb1",
        "status": "created",
        "message": "Notebook created",
        "server_url": "https://cluster-a.example",
    }

    monkeypatch.setattr(
        notebook_crud.jupyterhub_sdk,
        "create_notebook_server",
        AsyncMock(return_value=jhub_result),
    )

    sdk = NotebookSDK()

    result = await sdk.create_notebook(
        ctx=ctx,
        cluster_name="cluster-a",
        username="user",
        server_name="nb1",
        server_options={"partition": "compute"},
    )

    assert result["status"] == "created"
    assert result["partition"] == "compute"
    assert "fallback" in result["message"].lower()


@pytest.mark.asyncio
async def test_notebook_sdk_create_notebook_rejects_invalid_memory(
    monkeypatch: pytest.MonkeyPatch,
):
    """Invalid memory specifications should surface a user-friendly Abort."""
    ctx = Mock(spec=typer.Context)
    ctx.obj = SimpleNamespace(profile="default", settings=Mock())

    def _fail_client(
        *_args: object, **_kwargs: object
    ) -> None:  # pragma: no cover - ensure not called
        raise AssertionError("GraphQL should not be invoked when memory parsing fails")

    monkeypatch.setattr(
        "vantage_cli.sdk.notebook.crud.create_async_graphql_client",
        Mock(side_effect=_fail_client),
    )

    sdk = NotebookSDK()

    with pytest.raises(Abort) as excinfo:
        await sdk.create_notebook(
            ctx=ctx,
            cluster_name="cluster-a",
            username="user",
            server_name="nb1",
            server_options={
                "partition": "compute",
                "memory": "4Z",  # Unsupported unit
            },
        )

    assert "Invalid memory specification" in str(excinfo.value)
