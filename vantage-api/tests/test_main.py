"""Core module for testing the Sentry initialization and the health check endpoint."""
import logging
from unittest import mock

import pytest
from fastapi import status
from httpx import AsyncClient

from api.main import init_sentry_integration


@pytest.mark.asyncio
async def test_health_check(test_client: AsyncClient):
    """Test the health check route.

    This test ensures the API has a health check path configured properly, so
    the production and staging environments can configure the load balancing.
    """
    response = await test_client.get("/health")

    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_sentry_integration__check_if_no_exception_is_raised_when_in_testing_mode():
    """Test if no exception is raised when in testing mode while initializing Sentry."""
    try:
        await init_sentry_integration()
    except:  # noqa: E722
        assert False, "Exception was raised when trying to initialize Sentry"


@mock.patch("api.main.SETTINGS")
@mock.patch("api.main.sentry_sdk")
@mock.patch("sentry_sdk.integrations.httpx.HttpxIntegration")
@mock.patch("sentry_sdk.integrations.logging.LoggingIntegration")
@mock.patch("sentry_sdk.integrations.sqlalchemy.SqlalchemyIntegration")
@pytest.mark.asyncio
async def test_sentry_integration__check_if_sentry_is_initialized_correctly(
    mocked_sql_integration: mock.Mock,
    mocked_logging_integration: mock.Mock,
    mocked_httpx_integration: mock.Mock,
    mocked_sentry_sdk: mock.Mock,
    mocked_settings: mock.Mock,
):
    """Test if Sentry is initialized correctly."""
    dsn = "http://omnivector.solutions"
    sample_rate = 1

    mocked_settings.TEST_ENV = False
    mocked_settings.SENTRY_DSN = dsn
    mocked_settings.SENTRY_TRACES_SAMPLE_RATE = sample_rate
    mocked_settings.STAGE = "testing"
    mocked_settings.SENTRY_SAMPLE_RATE = sample_rate
    mocked_settings.SENTRY_PROFILING_SAMPLE_RATE = sample_rate

    mocked_sentry_sdk.init = mock.Mock(return_value=None)

    mocked_httpx_integration.return_value = None
    mocked_logging_integration.return_value = None
    mocked_sql_integration.return_value = None

    await init_sentry_integration()

    mocked_sentry_sdk.init.assert_called_once_with(
        dsn=dsn,
        integrations=[None, None, None],
        sample_rate=sample_rate,
        profiles_sample_rate=sample_rate,
        traces_sample_rate=sample_rate,
        environment="testing",
        enable_tracing=True,
    )
    mocked_httpx_integration.assert_called_once_with()
    mocked_logging_integration.assert_called_once_with(level=logging.WARNING, event_level=logging.ERROR)
    mocked_sql_integration.assert_called_once_with()
