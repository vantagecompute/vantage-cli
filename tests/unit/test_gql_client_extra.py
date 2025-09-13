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
from types import SimpleNamespace

import pytest

from vantage_cli.gql_client import (
    AuthenticationError,
    GraphQLClientConfig,
    GraphQLError,
    QueryMetrics,
    VantageGraphQLClient,
)


class DummySettings(SimpleNamespace):
    pass


def make_client(require_persona: bool = True) -> VantageGraphQLClient:
    token_set = SimpleNamespace(access_token="header.payload.sig", refresh_token="r1")
    persona = SimpleNamespace(token_set=token_set) if require_persona else None
    config = GraphQLClientConfig(url="https://example.com/graphql", fetch_schema=True)
    client = VantageGraphQLClient(
        config=config, persona=persona, profile="test", settings=DummySettings()
    )
    return client


class FakeSession:
    def __init__(self, results_or_errors):
        self._items = list(results_or_errors)
        self.schema = {"__schema": {}}

    async def execute(self, *_args, **_kwargs):
        if not self._items:
            return {}
        item = self._items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class FakeAsyncSessionCM:
    def __init__(self, session: FakeSession):
        self._session = session

    async def __aenter__(self):
        """Return underlying fake session (test helper)."""
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        """Do not suppress exceptions (return False)."""
        return False


@pytest.mark.asyncio
async def test_execute_async_success_no_auth(monkeypatch):
    client = make_client()

    # Bypass auth validation
    monkeypatch.setattr(client, "_validate_auth", lambda: None)
    monkeypatch.setattr(
        client, "_async_session", lambda: FakeAsyncSessionCM(FakeSession([{"data": {"ok": True}}]))
    )

    result = await client.execute_async("query Test { field }", require_auth=False)
    assert result == {"data": {"ok": True}}
    metrics = client.get_metrics()
    assert len(metrics) == 1 and metrics[0].success is True


@pytest.mark.asyncio
async def test_execute_async_graphql_error(monkeypatch):
    client = make_client()
    monkeypatch.setattr(client, "_validate_auth", lambda: None)
    # Return a result with errors key
    monkeypatch.setattr(
        client,
        "_async_session",
        lambda: FakeAsyncSessionCM(FakeSession([{"errors": ["boom"], "data": None}])),
    )
    with pytest.raises(GraphQLError):
        await client.execute_async("query Err { x }", require_auth=False)
    # Metrics should show failure
    m = client.get_metrics()
    assert len(m) == 1 and m[0].success is False and m[0].error_type == "GraphQLError"


@pytest.mark.asyncio
async def test_execute_async_auth_retry_success(monkeypatch):
    from gql.transport.exceptions import TransportServerError

    client = make_client()
    # Avoid real auth validation complexity
    monkeypatch.setattr(client, "_validate_auth", lambda: None)
    # First attempt raises auth error, second returns success
    auth_error = TransportServerError("401 Unauthorized")

    async def refresh_ok(_settings):
        return True

    monkeypatch.setattr(client, "_refresh_token_async", refresh_ok)
    monkeypatch.setattr(client, "_refresh_transport_headers", lambda: None)
    # IMPORTANT: reuse the SAME session instance across retry so that the second
    # execute() call sees the success result instead of re-raising the auth error.
    session = FakeSession([auth_error, {"data": {"ok": True}}])
    monkeypatch.setattr(client, "_async_session", lambda: FakeAsyncSessionCM(session))

    result = await client.execute_async("query NeedsAuth { y }", require_auth=True)
    assert result["data"]["ok"] is True
    metrics = client.get_metrics()
    # Only one metrics entry (first attempt skipped due to retry) with retry_count=1
    assert len(metrics) == 1 and metrics[0].retry_count == 1 and metrics[0].success is True


@pytest.mark.asyncio
async def test_execute_async_auth_retry_failure(monkeypatch):
    from gql.transport.exceptions import TransportServerError

    client = make_client()
    monkeypatch.setattr(client, "_validate_auth", lambda: None)
    auth_error = TransportServerError("401 Unauthorized")

    # Refresh fails
    async def refresh_fail(_settings):
        return False

    monkeypatch.setattr(client, "_refresh_token_async", refresh_fail)
    monkeypatch.setattr(
        client,
        "_async_session",
        lambda: FakeAsyncSessionCM(FakeSession([auth_error])),
    )
    with pytest.raises(AuthenticationError):
        await client.execute_async("query NeedsAuth { y }", require_auth=True)
    metrics = client.get_metrics()
    assert (
        len(metrics) == 1
        and metrics[0].success is False
        and metrics[0].error_type == "TransportServerError"
    )


@pytest.mark.asyncio
async def test_handle_transport_errors(monkeypatch):
    from gql.transport.exceptions import (
        TransportClosed,
        TransportConnectionFailed,
        TransportServerError,
    )
    from requests.exceptions import Timeout

    client = make_client()
    monkeypatch.setattr(client, "_validate_auth", lambda: None)

    error_cases = [
        (TransportServerError("403 Forbidden"), AuthenticationError),
        (TransportServerError("500 Internal"), GraphQLError),
        (TransportConnectionFailed("conn fail"), GraphQLError),
        (Timeout("timeout"), GraphQLError),
        (TransportClosed("closed"), GraphQLError),
    ]

    for exc, expected in error_cases:
        # Each execution returns the exception raising path
        monkeypatch.setattr(client, "clear_metrics", lambda: None)
        monkeypatch.setattr(client, "_query_metrics", [])
        monkeypatch.setattr(
            client,
            "_async_session",
            lambda exc=exc: FakeAsyncSessionCM(FakeSession([exc])),
        )
        with pytest.raises(expected):
            await client.execute_async("query Err { z }", require_auth=False)
        assert client.get_metrics()[0].success is False


def test_metrics_clear():
    client = make_client()
    # Manually log two metrics
    client._log_query_metrics(QueryMetrics("A", 10.0, True))
    client._log_query_metrics(QueryMetrics("B", 5.0, False, error_type="X"))
    assert len(client.get_metrics()) == 2
    client.clear_metrics()
    assert client.get_metrics() == []


@pytest.mark.asyncio
async def test_get_schema_success(monkeypatch):
    client = make_client()

    fake_session = FakeSession([{}])
    monkeypatch.setattr(
        client,
        "_async_session",
        lambda: FakeAsyncSessionCM(fake_session),
    )
    schema = await client.get_schema()
    assert schema == fake_session.schema


@pytest.mark.asyncio
async def test_get_schema_fetch_disabled(monkeypatch):
    client = make_client()
    client.config.fetch_schema = False
    schema = await client.get_schema()
    assert schema is None


@pytest.mark.asyncio
async def test_health_check_failure(monkeypatch):
    client = make_client()

    async def fail_execute(*_a, **_k):
        raise GraphQLError("boom")

    monkeypatch.setattr(client, "execute_async", fail_execute)
    ok = await client.health_check()
    assert ok is False
