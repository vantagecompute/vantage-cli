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
"""Additional coverage tests for `vantage_cli.gql_client` focusing on previously uncovered branches.

These tests deliberately patch internal methods to exercise code paths that are otherwise
hard to hit (e.g., token refresh success, logging branches, query name extraction edge cases).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict

import pytest
from graphql import parse as gql_parse
from jose import exceptions as jwt_exceptions

from vantage_cli.gql_client import (
    GraphQLClientConfig,
    VantageGraphQLClient,
    create_async_graphql_client,
    create_production_client,
)
from vantage_cli.schemas import IdentityData, Persona, TokenSet


def _make_persona(
    email: str = "u@example.com",
    client_id: str = "cid",
    access: str | None = "tok",
    refresh: str | None = "rt",
) -> Persona:
    return Persona(
        token_set=TokenSet(access_token=access, refresh_token=refresh),
        identity_data=IdentityData(email=email, client_id=client_id),
    )


class TestInitAndLoggingBranches:
    def test_init_disable_logging_branch(self, monkeypatch):
        """Cover branch where enable_logging=False (line 137 skipped)."""
        cfg = GraphQLClientConfig(url="https://example/graphql", enable_logging=False)
        with monkeypatch.context() as m:
            m.setenv("PYTHONHASHSEED", "0")  # no-op just showing context usage
            client = VantageGraphQLClient(config=cfg)
        # _setup_logging should not create _client and no exception
        assert client.config.enable_logging is False

    def test_log_query_metrics_disable_logging(self):
        """Exercise _log_query_metrics when logging disabled (line 246 skip)."""
        cfg = GraphQLClientConfig(url="u", enable_logging=False)
        client = VantageGraphQLClient(cfg)
        # Manually create metrics object
        from vantage_cli.gql_client import QueryMetrics

        metrics = QueryMetrics(query_name="Q", execution_time_ms=1.23, success=True)
        client._log_query_metrics(metrics)  # should append only
        assert client.get_metrics() and client.get_metrics()[0].query_name == "Q"


class TestTransportAndHeaders:
    def test_create_transport_adds_auth_header(self, monkeypatch):
        persona = _make_persona()
        cfg = GraphQLClientConfig(url="https://api/graphql")
        client = VantageGraphQLClient(cfg, persona=persona)

        captured: Dict[str, Any] = {}

        class DummyTransport:
            def __init__(self, url, headers, timeout, ssl):  # noqa: D401 signature compatibility
                # Use literal to satisfy C408 (dict literal instead of dict()).
                captured.update({"url": url, "headers": headers, "timeout": timeout, "ssl": ssl})

        monkeypatch.setattr("vantage_cli.gql_client.AIOHTTPTransport", DummyTransport)
        t = client._create_transport()
        assert captured["headers"]["Authorization"] == f"Bearer {persona.token_set.access_token}"
        assert (
            t is None
        )  # DummyTransport returns None implicitly; presence of header is what matters

    def test_refresh_transport_headers(self, monkeypatch):
        persona = _make_persona()
        cfg = GraphQLClientConfig(url="https://api/graphql")
        client = VantageGraphQLClient(cfg, persona=persona)
        flag = {"called": False}

        def fake_create():
            flag["called"] = True
            return "TRANSPORT"

        monkeypatch.setattr(client, "_create_transport", fake_create)
        client._refresh_transport_headers()
        assert flag["called"] is True
        assert client._transport == "TRANSPORT"


class TestAuthValidationAndExpiry:
    def test_validate_auth_expired_token(self, monkeypatch):
        persona = _make_persona(access="expired", refresh="rt")
        cfg = GraphQLClientConfig(url="u")
        client = VantageGraphQLClient(cfg, persona=persona)

        def fake_decode(*a, **k):  # always raise expiry
            raise jwt_exceptions.ExpiredSignatureError("expired")

        monkeypatch.setattr("vantage_cli.gql_client.jwt.decode", fake_decode)
        with pytest.raises(Exception) as exc:
            client._validate_auth()
        assert "expired" in str(exc.value).lower()

    def test_validate_auth_passes_when_valid(self, monkeypatch):
        persona = _make_persona(access="valid")
        cfg = GraphQLClientConfig(url="u")
        client = VantageGraphQLClient(cfg, persona=persona)

        monkeypatch.setattr(
            "vantage_cli.gql_client.jwt.decode",
            lambda *a, **k: {"sub": "x"},  # decode success => not expired
        )
        # Should not raise
        client._validate_auth()

    def test_is_token_expired_no_persona(self):
        cfg = GraphQLClientConfig(url="u")
        client = VantageGraphQLClient(cfg, persona=None)
        assert client._is_token_expired() is True  # line 192

    def test_is_token_expired_valid(self, monkeypatch):
        persona = _make_persona(access="ok")
        cfg = GraphQLClientConfig(url="u")
        client = VantageGraphQLClient(cfg, persona=persona)
        monkeypatch.setattr("vantage_cli.gql_client.jwt.decode", lambda *a, **k: {"ok": True})
        assert client._is_token_expired() is False  # line 201


class TestTokenRefreshAsync:
    @pytest.mark.asyncio
    async def test_refresh_token_async_success(self, monkeypatch):
        persona = _make_persona(access="a", refresh="r")
        cfg = GraphQLClientConfig(url="u")
        client = VantageGraphQLClient(cfg, persona=persona, profile="p1")

        monkeypatch.setattr(
            "vantage_cli.gql_client.refresh_access_token_standalone", lambda *a, **k: True
        )
        called = {"saved": False}

        def fake_save(profile, token_set):  # noqa: D401
            called["saved"] = True

        monkeypatch.setattr("vantage_cli.gql_client.save_tokens_to_cache", fake_save)
        ok = await client._refresh_token_async(settings=SimpleNamespace())
        assert ok is True
        assert called["saved"] is True  # lines 225-227

    @pytest.mark.asyncio
    async def test_refresh_token_async_failure(self, monkeypatch):
        persona = _make_persona(access="a", refresh="r")
        cfg = GraphQLClientConfig(url="u")
        client = VantageGraphQLClient(cfg, persona=persona)

        monkeypatch.setattr(
            "vantage_cli.gql_client.refresh_access_token_standalone", lambda *a, **k: False
        )
        ok = await client._refresh_token_async(settings=SimpleNamespace())
        assert ok is False


class TestQueryNameExtraction:
    def test_extract_query_name_from_string(self):
        cfg = GraphQLClientConfig(url="u")
        client = VantageGraphQLClient(cfg)
        name = client._extract_query_name("query GetItems { items }")
        assert name == "GetItems"

    def test_extract_query_name_from_document_node(self):
        cfg = GraphQLClientConfig(url="u")
        client = VantageGraphQLClient(cfg)
        doc = gql_parse("query FetchData { field }")
        name = client._extract_query_name(doc)
        assert name == "FetchData"

    def test_extract_mutation_name(self):
        cfg = GraphQLClientConfig(url="u")
        client = VantageGraphQLClient(cfg)
        name = client._extract_query_name("mutation DoThing { run }")
        assert name == "DoThing"

    def test_extract_query_name_unnamed(self):
        cfg = GraphQLClientConfig(url="u")
        client = VantageGraphQLClient(cfg)
        name = client._extract_query_name("query { items }")
        assert name == "UnnamedOperation"


class TestAsyncSessionAndExecute:
    @pytest.mark.asyncio
    async def test_async_session_creates_transport(self, monkeypatch):
        cfg = GraphQLClientConfig(url="u")
        client = VantageGraphQLClient(cfg)
        created = {"transport": False}

        def fake_create():
            created["transport"] = True
            return SimpleNamespace()

        monkeypatch.setattr(client, "_create_transport", fake_create)

        class DummySession:
            async def __aenter__(self):
                return SimpleNamespace(execute=lambda *a, **k: {"data": {}})

            async def __aexit__(self, exc_type, exc, tb):
                return False

        class DummyClient:
            def __init__(self, transport, fetch_schema_from_transport):
                self.transport = transport
                self.fetch_schema_from_transport = fetch_schema_from_transport

            async def __aenter__(self):  # returns session
                return DummySession()

            async def __aexit__(self, exc_type, exc, tb):
                return False

        monkeypatch.setattr("vantage_cli.gql_client.Client", DummyClient)
        async with client._async_session():
            pass
        assert created["transport"] is True  # lines 322-325

    @pytest.mark.asyncio
    async def test_execute_async_success_metrics(self, monkeypatch):
        persona = _make_persona(access="tok")
        cfg = GraphQLClientConfig(url="u")
        client = VantageGraphQLClient(cfg, persona=persona)

        # Bypass auth expiration
        monkeypatch.setattr(client, "_is_token_expired", lambda: False)

        class DummySession:
            async def execute(self, *a, **k):
                return {"value": 1}

        class DummyClient:
            def __init__(self, transport, fetch_schema_from_transport):
                pass

            async def __aenter__(self):
                return DummySession()

            async def __aexit__(self, exc_type, exc, tb):
                return False

        monkeypatch.setattr("vantage_cli.gql_client.Client", DummyClient)
        result = await client.execute_async("query Q { a }")
        assert result["value"] == 1  # lines 369-372 path
        assert client.get_metrics() and client.get_metrics()[0].success is True


class TestHealthAndFactories:
    @pytest.mark.asyncio
    async def test_health_check_success(self, monkeypatch):
        cfg = GraphQLClientConfig(url="u")
        client = VantageGraphQLClient(cfg)
        monkeypatch.setattr(client, "execute_async", lambda *a, **k: {"__schema": {}})
        assert await client.health_check() is True  # line 469

    def test_create_production_client_path(self):
        persona = _make_persona()
        client = create_production_client(url="https://api/graphql", persona=persona)
        assert isinstance(client, VantageGraphQLClient)

    def test_create_async_graphql_client_success(self, monkeypatch):
        settings = SimpleNamespace(api_base_url="https://api")
        persona = _make_persona()
        monkeypatch.setattr(
            "vantage_cli.gql_client.load_tokens_from_cache", lambda p: persona.token_set
        )
        monkeypatch.setattr("vantage_cli.gql_client.extract_persona", lambda p, t, s: persona)
        client = create_async_graphql_client(settings=settings, profile="prof")
        assert isinstance(client, VantageGraphQLClient)  # lines 605-624
