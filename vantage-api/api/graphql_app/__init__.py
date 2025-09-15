"""Definition of the GraphQL schema."""
import strawberry
from strawberry.schema.config import StrawberryConfig

from api.graphql_app.extensions import HideAttributeErrors
from api.graphql_app.queries import Query
from api.graphql_app.mutations import Mutation

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    config=StrawberryConfig(auto_camel_case=True),
    extensions=[
        HideAttributeErrors
    ]
)
