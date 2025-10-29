"""Unit tests for the JupyterHub client."""

from types import SimpleNamespace
from typing import Dict
from unittest.mock import AsyncMock

import pytest

from vantage_cli.exceptions import Abort
from vantage_cli.jupyterhub_client import JupyterHubClient


@pytest.mark.asyncio
async def test_create_user_server_404_includes_hint(monkeypatch: pytest.MonkeyPatch):
    """A 404 response should surface guidance for diagnosing missing JupyterHub servers."""
    client = JupyterHubClient("https://example.com", "token")

    def response_json() -> Dict[str, str]:
        return {}

    response = SimpleNamespace(
        status_code=404,
        text='{"status": 404, "message": "Not Found"}',
        json=response_json,
    )

    mock_post = AsyncMock(return_value=response)
    mock_close = AsyncMock()

    monkeypatch.setattr(client.client, "post", mock_post)
    monkeypatch.setattr(client.client, "aclose", mock_close)

    with pytest.raises(Abort) as excinfo:
        await client.create_user_server(username="alice", server_name="named")

    message = str(excinfo.value)
    assert "JupyterHub returned 404" in message
    assert "named" in message

    await client.close()
    mock_close.assert_awaited_once()
