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
import time
from types import SimpleNamespace

import pytest
from jose import jwt

from vantage_cli.gql_client import (
    AuthenticationError,
    GraphQLClientConfig,
    GraphQLError,
    VantageGraphQLClient,
    create_async_graphql_client,
)


class DummySettings(SimpleNamespace):
    pass


def make_client(persona=True, access_token="tok", refresh_token="rt"):
    person = None
    if persona:
        token_set = SimpleNamespace(access_token=access_token, refresh_token=refresh_token)
        person = SimpleNamespace(token_set=token_set)
    config = GraphQLClientConfig(url="https://example.com/graphql", fetch_schema=True)
    return VantageGraphQLClient(
        config=config, persona=person, profile="tail", settings=DummySettings()
    )


# -------------------- _validate_auth and _is_token_expired paths --------------------


def test_validate_auth_no_persona():
    client = make_client(persona=False)
    with pytest.raises(AuthenticationError):
        client._validate_auth()  # type: ignore


def test_validate_auth_no_access_token():
    # persona exists but token missing
    client = make_client(access_token="")
    with pytest.raises(AuthenticationError):
        client._validate_auth()  # type: ignore


def test_validate_auth_expired_token():
    # Build an expired JWT (exp in the past). Signature not verified.
    expired = jwt.encode({"exp": int(time.time()) - 10}, key="", algorithm="HS256")
    client = make_client(access_token=expired)
    with pytest.raises(AuthenticationError):
        client._validate_auth()  # type: ignore


def test_is_token_expired_invalid_format(monkeypatch):
    # Provide a token that will trigger generic JWTError (malformed token)
    client = make_client(access_token="not.a.jwt")
    assert client._is_token_expired() is True  # type: ignore


# -------------------- _refresh_token_async branches --------------------


@pytest.mark.asyncio
async def test_refresh_token_async_no_persona():
    client = make_client(persona=False)
    ok = await client._refresh_token_async(DummySettings())  # type: ignore
    assert ok is False


@pytest.mark.asyncio
async def test_refresh_token_async_refresh_false(monkeypatch):
    client = make_client()
    # Force underlying refresh to return False
    monkeypatch.setattr(
        "vantage_cli.gql_client.refresh_access_token_standalone", lambda *_a, **_k: False
    )
    ok = await client._refresh_token_async(DummySettings())  # type: ignore
    assert ok is False


@pytest.mark.asyncio
async def test_refresh_token_async_exception(monkeypatch):
    client = make_client()

    def boom(*_a, **_k):
        raise RuntimeError("boom")

    monkeypatch.setattr("vantage_cli.gql_client.refresh_access_token_standalone", boom)
    ok = await client._refresh_token_async(DummySettings())  # type: ignore
    assert ok is False


# -------------------- get_schema exception path --------------------


@pytest.mark.asyncio
async def test_get_schema_exception(monkeypatch):
    client = make_client()

    class FailingCM:
        async def __aenter__(self):  # pragma: no cover - trivial
            raise RuntimeError("fail schema")

        async def __aexit__(self, exc_type, exc, tb):  # pragma: no cover - trivial
            return False

    monkeypatch.setattr(client, "_async_session", lambda: FailingCM())
    schema = await client.get_schema()
    assert schema is None


# -------------------- execute_async unknown transport error (fallback) --------------------


class WeirdError(Exception):
    pass


@pytest.mark.asyncio
async def test_execute_async_unknown_transport_error(monkeypatch):
    client = make_client()
    # Skip auth check complexity
    monkeypatch.setattr(client, "_validate_auth", lambda: None)

    class FakeSession:
        async def execute(self, *_a, **_k):
            raise WeirdError("weird")

    class CM:
        async def __aenter__(self):
            return FakeSession()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(client, "_async_session", lambda: CM())
    with pytest.raises(GraphQLError) as ei:
        await client.execute_async("query X { x }", require_auth=False)
    assert "Transport error" in str(ei.value)
    # Metrics recorded failure
    m = client.get_metrics()
    assert len(m) == 1 and m[0].success is False and m[0].error_type == "WeirdError"


# -------------------- create_async_graphql_client failure path --------------------


def test_create_async_graphql_client_failure(monkeypatch):
    from vantage_cli import gql_client as gc

    settings = DummySettings(api_base_url="https://api.example.com")

    def load_fail(_profile):
        raise RuntimeError("cache boom")

    monkeypatch.setattr(gc, "load_tokens_from_cache", load_fail)
    with pytest.raises(RuntimeError):
        _ = create_async_graphql_client(settings, profile="default")
