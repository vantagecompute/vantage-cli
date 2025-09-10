#!/usr/bin/env python3
"""Integration tests for the GraphQL client.

This test validates that the cluster commands can successfully use the new
gql-based GraphQL client implementation.
"""

import sys
import traceback
from unittest.mock import Mock

from vantage_cli.gql_client import (
    GraphQLClientConfig,
    TransportType,
    VantageGraphQLClient,
    create_development_client,
    create_vantage_graphql_client,
)
from vantage_cli.schemas import Persona, TokenSet


def test_factory_functions():
    """Test that factory functions work correctly."""
    print("🔧 Testing factory functions...")

    # Test basic factory with aiohttp transport (now the only option)
    client = create_vantage_graphql_client(
        url="https://api.example.com/graphql", transport_type=TransportType.AIOHTTP
    )
    assert isinstance(client, VantageGraphQLClient)
    assert client.config.url == "https://api.example.com/graphql"
    print("✅ Basic factory function works")

    # Test development factory
    dev_client = create_development_client(url="http://localhost:8000/graphql")
    assert isinstance(dev_client, VantageGraphQLClient)
    assert dev_client.config.verify_ssl is False
    assert dev_client.config.log_queries is True
    print("✅ Development factory function works")


def test_configuration_options():
    """Test various configuration options."""
    print("\n⚙️ Testing configuration options...")

    # Test custom headers
    config = GraphQLClientConfig(
        url="https://api.example.com/graphql",
        headers={"X-Custom": "test"},
        timeout=60,
        max_retries=5,
    )
    client = VantageGraphQLClient(config=config)

    headers = client._build_headers()
    assert "X-Custom" in headers
    assert headers["X-Custom"] == "test"
    assert client.config.timeout == 60
    assert client.config.max_retries == 5
    print("✅ Custom configuration works")


def test_authentication_integration():
    """Test authentication integration."""
    print("\n🔐 Testing authentication integration...")

    # Mock persona and token
    mock_token_set = Mock(spec=TokenSet)
    mock_token_set.access_token = "mock.jwt.token"

    mock_persona = Mock(spec=Persona)
    mock_persona.token_set = mock_token_set

    client = create_vantage_graphql_client(
        url="https://api.example.com/graphql", persona=mock_persona
    )

    headers = client._build_headers()
    assert headers["Authorization"] == "Bearer mock.jwt.token"
    print("✅ Authentication integration works")


def test_query_name_extraction():
    """Test query name extraction functionality."""
    print("\n🔍 Testing query name extraction...")

    client = create_development_client(url="https://api.example.com/graphql")

    test_cases = [
        ("query GetUser { user { id } }", "GetUser"),
        (
            "mutation CreateUser($input: UserInput!) { createUser(input: $input) { id } }",
            "CreateUser",
        ),
        ("query { users { id } }", "UnnamedOperation"),
        ("{ users { id } }", "UnnamedOperation"),
    ]

    for query, expected in test_cases:
        actual = client._extract_query_name(query)
        assert actual == expected, f"Expected {expected}, got {actual}"

    print("✅ Query name extraction works")


def test_metrics_collection():
    """Test metrics collection functionality."""
    print("\n📊 Testing metrics collection...")

    client = create_development_client(url="https://api.example.com/graphql")

    # Initially no metrics
    assert len(client.get_metrics()) == 0

    # Simulate adding metrics
    from vantage_cli.gql_client import QueryMetrics

    metric = QueryMetrics(query_name="TestQuery", execution_time_ms=123.45, success=True)
    client._log_query_metrics(metric)

    # Check metrics
    metrics = client.get_metrics()
    assert len(metrics) == 1
    assert metrics[0].query_name == "TestQuery"
    assert metrics[0].execution_time_ms == 123.45

    # Clear metrics
    client.clear_metrics()
    assert len(client.get_metrics()) == 0

    print("✅ Metrics collection works")


def test_cluster_commands_import():
    """Test that cluster commands can import and use the new client."""
    print("\n🗂️ Testing cluster commands integration...")

    try:
        # Test imports
        from vantage_cli.commands.cluster.delete import delete_cluster
        from vantage_cli.commands.cluster.get import get_cluster
        from vantage_cli.commands.cluster.list import list_clusters

        print("✅ Cluster command imports successful")

        # These functions should exist and be callable
        assert callable(list_clusters)
        assert callable(get_cluster)
        assert callable(delete_cluster)

        print("✅ Cluster commands are callable")

    except ImportError as e:
        print(f"❌ Cluster command import failed: {e}")
        raise


def test_error_handling():
    """Test error handling functionality."""
    print("\n🚨 Testing error handling...")

    from vantage_cli.gql_client import AuthenticationError, GraphQLError

    client = create_development_client(url="https://api.example.com/graphql")

    # Test GraphQL error handling
    result_with_errors = {"data": None, "errors": [{"message": "Field not found"}]}

    try:
        client._handle_graphql_errors(result_with_errors, "test query")
        assert False, "Should have raised GraphQLError"
    except GraphQLError as e:
        assert "Field not found" in str(e)
        print("✅ GraphQL error handling works")

    # Test authentication error
    client_no_auth = VantageGraphQLClient(
        config=GraphQLClientConfig(url="https://api.example.com/graphql")
    )

    try:
        client_no_auth._validate_auth()
        assert False, "Should have raised AuthenticationError"
    except AuthenticationError as e:
        assert "No authentication persona provided" in str(e)
        print("✅ Authentication error handling works")


def test_transport_types():
    """Test async transport type (now the only option)."""
    print("\n🚛 Testing transport types...")

    # Test aiohttp transport (now the only option)
    aiohttp_client = create_vantage_graphql_client(
        url="https://api.example.com/graphql", transport_type=TransportType.AIOHTTP
    )
    assert aiohttp_client.config.transport_type == TransportType.AIOHTTP
    print("✅ AIOHttp transport configuration works")

    # Test that async is the default behavior
    default_client = create_vantage_graphql_client(url="https://api.example.com/graphql")
    assert default_client.config.transport_type == TransportType.AIOHTTP
    print("✅ Async transport is default")


def run_all_tests():
    """Run all integration tests."""
    print("🚀 Starting GraphQL Client Integration Tests")
    print("=" * 60)

    test_functions = [
        test_factory_functions,
        test_configuration_options,
        test_authentication_integration,
        test_query_name_extraction,
        test_metrics_collection,
        test_cluster_commands_import,
        test_error_handling,
        test_transport_types,
    ]

    passed = 0
    failed = 0

    for test_func in test_functions:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} failed: {e}")
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All integration tests passed!")
        return True
    else:
        print(f"💥 {failed} tests failed!")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
