from types import SimpleNamespace
from typing import Any, Iterable

import pytest

from vantage_cli.commands.cluster import utils as cluster_utils


class DummyTokenSet:
    access_token = "token123"


class DummyPersona:
    token_set = DummyTokenSet()


class FakeResponse:
    def __init__(self, status_code: int, json_data: dict[str, Any] | None = None, text: str = ""):
        self.status_code: int = status_code
        self._json: dict[str, Any] = json_data or {}
        self.text: str = text or "{}"

    def json(self) -> dict[str, Any]:  # pragma: no cover - trivial
        return self._json


class FakeAsyncClient:
    def __init__(self, responses: Iterable[FakeResponse], boom: bool = False):
        self._responses: list[FakeResponse] = list(responses)
        self._boom: bool = boom

    async def __aenter__(self) -> "FakeAsyncClient":  # pragma: no cover - trivial
        """Enter async context returning self (test helper)."""
        return self

    async def __aexit__(self, *_exc: Any) -> bool:  # pragma: no cover - trivial
        """Exit async context without suppressing exceptions."""
        return False

    async def get(self, *_a: Any, **_k: Any) -> FakeResponse:
        if self._boom:
            raise RuntimeError("fail boom")
        return self._responses.pop(0)


def make_ctx():
    settings = SimpleNamespace(api_base_url="https://api.example.com")
    return SimpleNamespace(obj=SimpleNamespace(settings=settings, profile="dev"))


@pytest.mark.asyncio
async def test_get_cluster_client_secret_initial_non_200(monkeypatch):
    monkeypatch.setattr(cluster_utils, "extract_persona", lambda _p: DummyPersona())
    monkeypatch.setattr(
        cluster_utils.httpx,
        "AsyncClient",
        lambda *a, **k: FakeAsyncClient([FakeResponse(500, {"error": 1}, text="err")]),
    )
    ctx = make_ctx()
    secret = await cluster_utils.get_cluster_client_secret(ctx, "cid")
    assert secret is None


@pytest.mark.asyncio
async def test_get_cluster_client_secret_no_clients(monkeypatch):
    monkeypatch.setattr(cluster_utils, "extract_persona", lambda _p: DummyPersona())
    responses = [FakeResponse(200, {"clients": []})]
    monkeypatch.setattr(
        cluster_utils.httpx, "AsyncClient", lambda *a, **k: FakeAsyncClient(responses)
    )
    ctx = make_ctx()
    secret = await cluster_utils.get_cluster_client_secret(ctx, "cid")
    assert secret is None


@pytest.mark.asyncio
async def test_get_cluster_client_secret_missing_internal_id(monkeypatch):
    monkeypatch.setattr(cluster_utils, "extract_persona", lambda _p: DummyPersona())
    responses = [FakeResponse(200, {"clients": [{"clientId": "cid"}]})]
    monkeypatch.setattr(
        cluster_utils.httpx, "AsyncClient", lambda *a, **k: FakeAsyncClient(responses)
    )
    ctx = make_ctx()
    secret = await cluster_utils.get_cluster_client_secret(ctx, "cid")
    assert secret is None


@pytest.mark.asyncio
async def test_get_cluster_client_secret_secret_non_200(monkeypatch):
    monkeypatch.setattr(cluster_utils, "extract_persona", lambda _p: DummyPersona())
    responses = [
        FakeResponse(200, {"clients": [{"id": "123", "clientId": "cid"}]}),
        FakeResponse(404, text="not found"),
    ]
    monkeypatch.setattr(
        cluster_utils.httpx, "AsyncClient", lambda *a, **k: FakeAsyncClient(responses)
    )
    ctx = make_ctx()
    secret = await cluster_utils.get_cluster_client_secret(ctx, "cid")
    assert secret is None


@pytest.mark.asyncio
async def test_get_cluster_client_secret_secret_missing_value(monkeypatch):
    monkeypatch.setattr(cluster_utils, "extract_persona", lambda _p: DummyPersona())
    responses = [
        FakeResponse(200, {"clients": [{"id": "123", "clientId": "cid"}]}),
        FakeResponse(200, {"other": "x"}),
    ]
    monkeypatch.setattr(
        cluster_utils.httpx, "AsyncClient", lambda *a, **k: FakeAsyncClient(responses)
    )
    ctx = make_ctx()
    secret = await cluster_utils.get_cluster_client_secret(ctx, "cid")
    assert secret is None


@pytest.mark.asyncio
async def test_get_cluster_client_secret_success(monkeypatch):
    monkeypatch.setattr(cluster_utils, "extract_persona", lambda _p: DummyPersona())
    responses = [
        FakeResponse(200, {"clients": [{"id": "123", "clientId": "cid"}]}),
        FakeResponse(200, {"client_secret": "shhh"}),
    ]
    monkeypatch.setattr(
        cluster_utils.httpx, "AsyncClient", lambda *a, **k: FakeAsyncClient(responses)
    )
    ctx = make_ctx()
    secret = await cluster_utils.get_cluster_client_secret(ctx, "cid")
    assert secret == "shhh"


@pytest.mark.asyncio
async def test_get_cluster_client_secret_exception(monkeypatch):
    # Force exception inside function to hit exception block (line ~167)
    monkeypatch.setattr(cluster_utils, "extract_persona", lambda _p: DummyPersona())
    monkeypatch.setattr(
        cluster_utils.httpx, "AsyncClient", lambda *a, **k: FakeAsyncClient([], boom=True)
    )
    ctx = make_ctx()
    # Function returns None (typer.Exit() not raised) when exception occurs
    secret = await cluster_utils.get_cluster_client_secret(ctx, "cid")
    assert secret is None
