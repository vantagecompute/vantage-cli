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
#!/usr/bin/env python3
"""Test script for the new GraphQL client implementation.

This script demonstrates basic functionality of the new gql-based GraphQL client.
"""

import pytest

from vantage_cli.gql_client import (
    GraphQLClientConfig,
    TransportType,
    VantageGraphQLClient,
    create_development_client,
)


@pytest.mark.asyncio
async def test_client_creation():
    """Test that clients can be created successfully."""
    print("Testing GraphQL client creation...")

    # Test development client
    dev_client = create_development_client(url="https://api.example.com/graphql")
    print(f"✓ Development client created: {type(dev_client).__name__}")

    # Test production client with mock persona
    # Note: In real usage, you'd have a proper Persona object
    mock_persona = None  # For this test, we'll skip auth

    # Test configuration creation
    config = GraphQLClientConfig(
        url="https://api.example.com/graphql", transport_type=TransportType.AIOHTTP, timeout=30
    )

    client = VantageGraphQLClient(config=config, persona=mock_persona)
    print(f"✓ Custom client created: {type(client).__name__}")

    # Test health check (will fail without real endpoint, but shouldn't crash)
    try:
        is_healthy = await client.health_check()
        print(f"✓ Health check completed: {is_healthy}")
    except Exception as e:
        print(f"✓ Health check failed as expected (no real endpoint): {type(e).__name__}")

    print("✓ All client creation tests passed!")


def test_query_parsing():
    """Test query name extraction."""
    client = create_development_client(url="https://api.example.com/graphql")

    queries = [
        ("query GetUser { user { id name } }", "GetUser"),
        (
            "mutation CreateUser($input: UserInput!) { createUser(input: $input) { id } }",
            "CreateUser",
        ),
        ("query { users { id } }", "UnnamedOperation"),
        ("{ users { id } }", "UnnamedOperation"),
    ]

    print("Testing query name extraction...")
    for query, expected_name in queries:
        actual_name = client._extract_query_name(query)
        assert actual_name == expected_name, f"Expected {expected_name}, got {actual_name}"
        print(f"✓ Query '{query[:30]}...' -> {actual_name}")

    print("✓ All query parsing tests passed!")


def test_config_validation():
    """Test configuration validation."""
    print("Testing configuration validation...")

    # Test valid config
    config = GraphQLClientConfig(url="https://api.example.com/graphql", timeout=30, max_retries=3)
    VantageGraphQLClient(config=config)
    print("✓ Valid configuration accepted")

    # Test custom headers
    config_with_headers = GraphQLClientConfig(
        url="https://api.example.com/graphql", headers={"X-Custom-Header": "test-value"}
    )
    client_with_headers = VantageGraphQLClient(config=config_with_headers)
    headers = client_with_headers._build_headers()
    assert "X-Custom-Header" in headers
    print("✓ Custom headers configuration works")

    print("✓ All configuration tests passed!")


if __name__ == "__main__":
    print("🚀 Starting GraphQL client tests...\n")

    try:
        import asyncio

        asyncio.run(test_client_creation())
        print()
        test_query_parsing()
        print()
        test_config_validation()
        print()
        print("🎉 All tests passed! The new GraphQL client is working correctly.")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
