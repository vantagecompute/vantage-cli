"""Core module for defining the GraphQL extensions."""
from graphql.error import GraphQLError
from strawberry.extensions import SchemaExtension


def should_mask_error(error: GraphQLError) -> bool:
    """Determine if the error should be masked.

    Primarily used to mask AttributeError exceptions, which are raised when a field is accessed
    on a NoneType. For example, this can happen when a client requests `cloudAccount.name` and
    an existing cluster is not associated with a cloud account.
    """
    original_error = error.original_error
    if original_error and isinstance(original_error, AttributeError):
        return True
    return False


class HideAttributeErrors(SchemaExtension):
    """Hide AttributeErrors from the GraphQL response."""

    def on_request_end(self) -> None:
        """Hide AttributeError from the GraphQL response after the request is processed."""
        result = self.execution_context.result
        if result and result.errors:
            result.errors = list(filter(lambda error: not should_mask_error(error), result.errors))
            if result.errors == []:
                result.errors = None
