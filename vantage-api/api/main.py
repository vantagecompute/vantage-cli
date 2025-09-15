"""Main module for the API.

This module defines the FastAPI application and mounts the admin and cluster sub apps.
As well as, it configures the Sentry integration.
"""
import sentry_sdk
import toml
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware

from api.routers import (
    clients,
    cloud_accounts,
    graphql_router,
    groups,
    organizations,
    subscriptions,
    walkthrough,
)
from api.routers.roles import roles
from api.settings import SETTINGS
from api.sqs_app.sqs_listener import init_sqs_listeners
from api.utils.logging import logger

version = toml.load("pyproject.toml").get("tool").get("poetry").get("version")

# Admin API sub app
admin_api_subapp = FastAPI(title="Admin API", version=version)
admin_api_subapp.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# clients
admin_api_subapp.include_router(clients.router, tags=["Clients"], prefix="/management")

# organizations
admin_api_subapp.include_router(organizations.router, tags=["Organizations"], prefix="/management")

# roles
admin_api_subapp.include_router(roles.router, tags=["Roles"], prefix="/management")

# groups
admin_api_subapp.include_router(groups.router, tags=["Groups"], prefix="/management")

# cloud accounts
admin_api_subapp.include_router(cloud_accounts.router, tags=["Cloud Accounts"], prefix="/management")

# walkthrough
admin_api_subapp.include_router(walkthrough.router, tags=["Walkthrough"], prefix="/management")

# subscriptions
admin_api_subapp.include_router(subscriptions.router, tags=["Subscriptions"], prefix="/management")


# Cluster API sub app
cluster_api_subapp = FastAPI(title="Cluster API", version=version)
cluster_api_subapp.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# graphql
cluster_api_subapp.include_router(graphql_router, tags=["Cluster"])


app = FastAPI(version=version)


@app.on_event("startup")
async def init_sentry_integration():
    """Initiate the Sentry integration."""
    if SETTINGS.TEST_ENV is False and SETTINGS.SENTRY_DSN is not None:
        import logging

        from sentry_sdk.integrations.httpx import HttpxIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_logging = LoggingIntegration(level=logging.WARNING, event_level=logging.ERROR)

        sentry_sdk.init(
            dsn=SETTINGS.SENTRY_DSN,
            integrations=[sentry_logging, SqlalchemyIntegration(), HttpxIntegration()],
            sample_rate=SETTINGS.SENTRY_SAMPLE_RATE,
            profiles_sample_rate=SETTINGS.SENTRY_PROFILING_SAMPLE_RATE,
            traces_sample_rate=SETTINGS.SENTRY_TRACES_SAMPLE_RATE,
            environment=SETTINGS.STAGE,
            enable_tracing=True,
        )

        logger.debug("##### Sentry integration has been enabled.")
    else:
        logger.warning("##### Running in test env mode so Sentry integration is disabled.")


@app.on_event("startup")
async def init_listeners():
    """Initiate the sqs listeners."""
    if not SETTINGS.TEST_ENV:
        init_sqs_listeners()


@app.get(
    "/health",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={204: {"description": "API is healthy"}},
)
async def health():
    """Healthcheck, for health monitors in the deployed environment."""
    return Response(status_code=status.HTTP_204_NO_CONTENT)


app.mount("/admin", admin_api_subapp)
app.mount("/cluster", cluster_api_subapp)
