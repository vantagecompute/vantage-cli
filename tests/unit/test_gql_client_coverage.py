# type: ignore[file]
"""Additional coverage tests for `vantage_cli.gql_client`.

Exercises previously uncovered branches and lines.

Focus areas (from coverage report):
 - Client init logging disabled branch (line 137 false branch)
 - Authorization header insertion in _create_transport (line 153)
 - _validate_auth expired token raise (line 186)
 - _is_token_expired branches (lines 192, 201)
 - _refresh_token_async success path (225-227)
 - _refresh_transport_headers recreation (238-240)
 - _log_query_metrics when logging disabled (246 else path)
 - _extract_query_name DocumentNode path and error fallbacks (260, 270-271, 276-281)
 - _async_session transport creation path (322-325, 331)
 - execute_async success path metrics (369-372)
 - execute_async unexpected error fallback raising GraphQLError (426)
 - health_check success return True (469)
 - create_production_client config assembly (524-536)
 - create_async_graphql_client success path (605-624)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from gql import gql
from gql.transport.aiohttp import AIOHTTPTransport
from graphql import DocumentNode  # type: ignore

from vantage_cli.config import Settings
from vantage_cli.gql_client import (
    AuthenticationError,
    GraphQLClientConfig,
    GraphQLError,
    QueryMetrics,
    VantageGraphQLClient,
    create_async_graphql_client,
    create_production_client,
)
from vantage_cli.schemas import IdentityData, Persona, TokenSet


def make_persona(
    email: str = "u@example.com",
    client_id: str = "cid",
    access: str = "tok",
    refresh: str = "rtok",
) -> Persona:
    return Persona(
        token_set=TokenSet(access_token=access, refresh_token=refresh),
        identity_data=IdentityData(email=email, client_id=client_id),
    )


def test_init_disable_logging_branch():
    cfg = GraphQLClientConfig(url="http://x", enable_logging=False)
    with patch.object(VantageGraphQLClient, "_setup_logging") as m:  # type: ignore[attr-defined]
        VantageGraphQLClient(config=cfg)
        m.assert_not_called()


def test_create_transport_includes_auth_header():
    persona = make_persona()
    cfg = GraphQLClientConfig(url="http://api", enable_logging=False)
    client = VantageGraphQLClient(config=cfg, persona=persona)
    # Patch AIOHTTPTransport to capture headers
    with patch("vantage_cli.gql_client.AIOHTTPTransport", wraps=AIOHTTPTransport) as transport_cls:
        client._create_transport()  # type: ignore[attr-defined]
        assert transport_cls.call_args.kwargs["headers"]["Authorization"].startswith("Bearer ")


def test_validate_auth_expired_token_raises():
    persona = make_persona(access="expired")
    cfg = GraphQLClientConfig(url="http://api", enable_logging=False)
    client = VantageGraphQLClient(config=cfg, persona=persona)
    with patch.object(client, "_is_token_expired", return_value=True):  # type: ignore[attr-defined]
        with pytest.raises(AuthenticationError, match="expired"):
            client._validate_auth()  # type: ignore[attr-defined]


def test_is_token_expired_missing_persona_and_valid_flow():
    cfg = GraphQLClientConfig(url="http://api", enable_logging=False)
    client = VantageGraphQLClient(config=cfg)
    assert client._is_token_expired() is True  # type: ignore[attr-defined]  # line 192 path
    # Valid token path: patch jwt.decode to succeed
    persona = make_persona(access="valid")
    client.persona = persona
    with patch("vantage_cli.gql_client.jwt.decode") as dec:
        dec.return_value = {"sub": "x"}
        assert client._is_token_expired() is False  # type: ignore[attr-defined]  # line 201 path


@pytest.mark.asyncio
async def test_refresh_token_async_success_path():
    persona = make_persona()
    cfg = GraphQLClientConfig(url="http://api", enable_logging=False)
    client = VantageGraphQLClient(config=cfg, persona=persona, profile="p1")
    with (
        patch("vantage_cli.gql_client.refresh_access_token_standalone", return_value=True),
        patch("vantage_cli.gql_client.save_tokens_to_cache") as save_mock,
    ):
        ok = await client._refresh_token_async(Settings())  # type: ignore[attr-defined]
        assert ok is True
        save_mock.assert_called_once()


def test_refresh_transport_headers_recreates_transport():
    persona = make_persona()
    cfg = GraphQLClientConfig(url="http://api", enable_logging=False)
    client = VantageGraphQLClient(config=cfg, persona=persona)
    client._transport = MagicMock(spec=AIOHTTPTransport)  # type: ignore[attr-defined]
    sentinel = object()
    with patch.object(client, "_create_transport", return_value=sentinel):
        client._refresh_transport_headers()  # type: ignore[attr-defined]
        assert client._transport is sentinel  # type: ignore[attr-defined]


def test_log_query_metrics_logging_disabled_no_logger_calls():
    cfg = GraphQLClientConfig(url="http://api", enable_logging=False)
    client = VantageGraphQLClient(config=cfg)
    m = QueryMetrics(query_name="Q", execution_time_ms=1.0, success=True)
    with patch("vantage_cli.gql_client.logger") as lg:
        client._log_query_metrics(m)  # type: ignore[attr-defined]
        lg.info.assert_not_called()
    assert client.get_metrics()[0].query_name == "Q"


def test_extract_query_name_document_node_and_error_fallbacks():
    cfg = GraphQLClientConfig(url="http://api", enable_logging=False)
    client = VantageGraphQLClient(config=cfg)
    # DocumentNode path
    qreq = gql("query GetItems { items }")
    # Extract the underlying DocumentNode if present
    doc: DocumentNode = getattr(qreq, "document", qreq)  # type: ignore[assignment]
    assert isinstance(doc, DocumentNode)
    assert client._extract_query_name(doc) == "GetItems"  # type: ignore[attr-defined]
    # Malformed query path triggers except
    assert client._extract_query_name("query ") == "UnnamedOperation"  # type: ignore[attr-defined]
    assert client._extract_query_name("mutation ") == "UnnamedOperation"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_async_session_creates_transport_and_yields():
    cfg = GraphQLClientConfig(url="http://api", enable_logging=False, fetch_schema=False)
    client = VantageGraphQLClient(config=cfg)

    class DummySession:
        async def execute(self, *_, **__):
            return {"data": {}}

    dummy_session = DummySession()

    class DummyClient:
        def __init__(self, transport, fetch_schema_from_transport):  # type: ignore[unused-ignore]
            self.transport = transport

        async def __aenter__(self):
            return dummy_session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    with (
        patch("vantage_cli.gql_client.Client", DummyClient),
        patch.object(client, "_create_transport", return_value=object()) as create_t,
    ):
        async with client._async_session() as sess:  # type: ignore[attr-defined]
            assert sess is dummy_session
            create_t.assert_called_once()
            assert client._transport is not None  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_execute_async_success_metrics_and_result():
    cfg = GraphQLClientConfig(url="http://api", enable_logging=False, fetch_schema=False)
    persona = make_persona(access="tok")
    client = VantageGraphQLClient(config=cfg, persona=persona)

    class DummySession:
        async def execute(self, *_, **__):
            return {"data": {"ok": True}}

    dummy_session = DummySession()

    class DummyClient:
        def __init__(self, transport, fetch_schema_from_transport):
            self.transport = transport

        async def __aenter__(self):
            return dummy_session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    with (
        patch.object(client, "_validate_auth") as vauth,
        patch("vantage_cli.gql_client.Client", DummyClient),
    ):
        data = await client.execute_async("query GetX { x }", variables={"a": 1})
        assert data == {"data": {"ok": True}}
        vauth.assert_called_once()
        # Metrics captured
        m = client.get_metrics()[0]
        assert m.success is True and m.query_name == "GetX"


@pytest.mark.asyncio
async def test_execute_async_unexpected_error_reaches_fallback_raise():
    cfg = GraphQLClientConfig(url="http://api", enable_logging=False, fetch_schema=False)
    persona = make_persona(access="tok")
    client = VantageGraphQLClient(config=cfg, persona=persona)

    class DummyClient:
        def __init__(self, transport, fetch_schema_from_transport):
            pass

        async def __aenter__(self):
            class BoomSession:
                async def execute(self, *_, **__):
                    raise RuntimeError("boom")

            return BoomSession()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    # Patch _handle_transport_error to NO-OP so we hit the fallback raise at line 426
    with (
        patch("vantage_cli.gql_client.Client", DummyClient),
        patch.object(client, "_handle_transport_error", return_value=None),
        patch.object(client, "_validate_auth"),
    ):
        with pytest.raises(GraphQLError) as exc:
            await client.execute_async("query Q { f }")
        assert "Unexpected error" in str(exc.value)


@pytest.mark.asyncio
async def test_health_check_success_path():
    cfg = GraphQLClientConfig(url="http://api", enable_logging=False, fetch_schema=False)
    client = VantageGraphQLClient(config=cfg)
    with patch.object(client, "execute_async", return_value={"__schema": {}}):
        assert await client.health_check() is True


def test_create_production_client_configuration():
    persona = make_persona()
    client = create_production_client(url="http://api/graphql", persona=persona, timeout=10)
    assert isinstance(client, VantageGraphQLClient)
    assert client.config.timeout == 10  # override applied
    assert client.config.fetch_schema is False


def test_create_async_graphql_client_success_path():
    settings = Settings()
    with (
        patch(
            "vantage_cli.gql_client.load_tokens_from_cache",
            return_value=TokenSet(access_token="a", refresh_token="r"),
        ),
        patch("vantage_cli.gql_client.extract_persona", return_value=make_persona()),
    ):
        client = create_async_graphql_client(settings=settings, profile="prof")
        assert isinstance(client, VantageGraphQLClient)
        assert client.profile == "prof"
