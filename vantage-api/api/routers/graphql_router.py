"""Core module for defining the GraphQL router."""
from fastapi import APIRouter
from strawberry.fastapi import GraphQLRouter

from api.graphql_app import schema
from api.graphql_app.helpers import get_context

graphql_router = APIRouter(tags=["GraphQL"])
graphql_router.include_router(GraphQLRouter(schema, context_getter=get_context), prefix="/graphql")
