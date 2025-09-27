"""Tests for the notebook create command."""

from types import SimpleNamespace
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest
import typer

from vantage_cli.commands.notebook import create as notebook_create_module
from vantage_cli.schemas import IdentityData, Persona, TokenSet


@pytest.mark.asyncio
async def test_create_notebook_uses_persona_username():
    """The create command should derive the username from the persona email when omitted."""
    ctx = Mock(spec=typer.Context)
    ctx.obj = SimpleNamespace(
        profile="default",
        console=Mock(),
        formatter=Mock(),
        json_output=False,
    )

    persona = Persona(
        token_set=TokenSet(access_token="token", refresh_token="refresh"),
        identity_data=IdentityData(client_id="client", email="user@example.com", org_id="org"),
    )

    ctx.obj.formatter.render_get = Mock()
    ctx.obj.formatter.render_error = Mock()

    result_payload: Dict[str, Any] = {
        "cluster_name": "test123",
        "username": "user_examplecom",
        "server_name": "mybook",
        "partition": "compute",
        "status": "created",
        "message": "Notebook created",
        "server_url": "https://test123.example",
        "slurm_job_id": 1234,
    }

    with (
        patch("vantage_cli.auth.extract_persona", return_value=persona),
        patch.object(
            notebook_create_module.notebook_sdk,
            "create_notebook",
            AsyncMock(return_value=result_payload),
        ) as mock_sdk_create,
    ):
        await notebook_create_module.create_notebook(
            ctx,
            cluster_name="test123",
            server_name="mybook",
            partition="compute",
        )

    mock_sdk_create.assert_awaited_once()
    await_args = mock_sdk_create.await_args
    assert await_args is not None
    # Username is derived from email: user@example.com -> user_examplecom
    assert await_args.kwargs["username"] == "user_examplecom"
    assert await_args.kwargs["server_options"]["partition"] == "compute"

    ctx.obj.formatter.render_get.assert_called_once()
    call_kwargs = ctx.obj.formatter.render_get.call_args.kwargs
    assert call_kwargs["data"]["username"] == "user_examplecom"
    assert call_kwargs["resource_name"] == "Notebook Server"
    ctx.obj.console.print.assert_called()


@pytest.mark.asyncio
async def test_create_notebook_requires_server_name():
    """The command should surface a helpful error when --name is omitted."""
    ctx = Mock(spec=typer.Context)
    ctx.obj = SimpleNamespace(
        profile="default",
        console=Mock(),
        formatter=SimpleNamespace(render_get=Mock(), render_error=Mock()),
        json_output=False,
    )

    persona = Persona(
        token_set=TokenSet(access_token="token", refresh_token="refresh"),
        identity_data=IdentityData(client_id="client", email="user@example.com", org_id="org"),
    )

    with (
        patch("vantage_cli.auth.extract_persona", return_value=persona),
        pytest.raises(typer.Exit) as excinfo,
    ):
        await notebook_create_module.create_notebook(
            ctx,
            cluster_name="test123",
            partition="compute",
        )

    assert excinfo.value.exit_code == 1
    ctx.obj.formatter.render_get.assert_not_called()


@pytest.mark.asyncio
async def test_create_notebook_requires_partition():
    """The command should surface a helpful error when --partition is omitted."""
    ctx = Mock(spec=typer.Context)
    ctx.obj = SimpleNamespace(
        profile="default",
        console=Mock(),
        formatter=SimpleNamespace(render_get=Mock(), render_error=Mock()),
        json_output=False,
    )

    persona = Persona(
        token_set=TokenSet(access_token="token", refresh_token="refresh"),
        identity_data=IdentityData(client_id="client", email="user@example.com", org_id="org"),
    )

    with (
        patch("vantage_cli.auth.extract_persona", return_value=persona),
        pytest.raises(typer.Exit) as excinfo,
    ):
        await notebook_create_module.create_notebook(
            ctx,
            cluster_name="test123",
            server_name="mybook",
        )

    assert excinfo.value.exit_code == 1
    ctx.obj.formatter.render_get.assert_not_called()


@pytest.mark.asyncio
async def test_create_notebook_handles_existing_notebook():
    """If the SDK returns an existing notebook, the command should render it."""
    ctx = Mock(spec=typer.Context)
    ctx.obj = SimpleNamespace(
        profile="default",
        console=Mock(),
        formatter=Mock(),
        json_output=False,
    )

    persona = Persona(
        token_set=TokenSet(access_token="token", refresh_token="refresh"),
        identity_data=IdentityData(client_id="client", email="user@example.com", org_id="org"),
    )

    existing_payload: Dict[str, Any] = {
        "cluster_name": "test123",
        "username": "ubuntu",
        "server_name": "mybook",
        "partition": "compute",
        "status": "exists",
        "message": "Notebook server already exists; returning existing record.",
        "server_url": "https://test123.example",
    }

    ctx.obj.formatter.render_get = Mock()

    with (
        patch("vantage_cli.auth.extract_persona", return_value=persona),
        patch.object(
            notebook_create_module.notebook_sdk,
            "create_notebook",
            AsyncMock(return_value=existing_payload),
        ),
    ):
        await notebook_create_module.create_notebook(
            ctx,
            cluster_name="test123",
            server_name="mybook",
            partition="compute",
            username="ubuntu",
        )

    ctx.obj.formatter.render_get.assert_called_once()
    call_kwargs = ctx.obj.formatter.render_get.call_args.kwargs
    assert call_kwargs["data"]["status"] == "exists"
    ctx.obj.console.print.assert_called()
    assert "already exists" in ctx.obj.console.print.call_args.args[0]
