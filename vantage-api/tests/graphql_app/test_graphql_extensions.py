"""Tests for the GraphQL extensions."""

from typing import Type

import pytest
from graphql.error import GraphQLError

from api.graphql_app.extensions import should_mask_error


@pytest.mark.parametrize(
    "error_class",
    [
        AttributeError,
        KeyError,
        IndexError,
        TypeError,
        ValueError,
    ],
)
def test_should_mask_error(error_class: Type[Exception]):
    """Test the should_mask_error function."""
    error = error_class("dummy")
    graphql_error = GraphQLError(message="dummy", original_error=error)
    if isinstance(error, AttributeError):
        assert should_mask_error(graphql_error)
    else:
        assert not should_mask_error(graphql_error)
