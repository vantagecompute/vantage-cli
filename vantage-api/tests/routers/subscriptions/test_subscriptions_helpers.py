"""Core module for testing subscriptions routers helpers."""
from unittest import mock

import pytest

from api.routers.subscriptions.helpers import (
    get_pending_aws_subscription_by_organization_id,
    get_subscription_by_id,
    get_subscription_by_organization_id,
    get_tier_id_by_name,
    get_type_id_by_name,
)
from api.sql_app.enums import SubscriptionTiersNames, SubscriptionTypesNames


@pytest.mark.asyncio
@pytest.mark.parametrize("tier", list(SubscriptionTiersNames))
async def test_get_tier_id_by_name(tier: SubscriptionTiersNames):
    """Test get_tier_id_by_name."""
    mocked_session = mock.AsyncMock()
    mocked_session.execute = mock.AsyncMock()
    mocked_session.execute.return_value.scalar_one_or_none = mock.Mock()
    mocked_session.execute.return_value.scalar_one_or_none.return_value = 1
    assert await get_tier_id_by_name(mocked_session, tier) == 1
    mocked_session.execute.assert_awaited_once()
    mocked_session.execute.return_value.scalar_one_or_none.assert_called_once_with()


@pytest.mark.asyncio
@pytest.mark.parametrize("type", list(SubscriptionTypesNames))
async def test_get_type_id_by_name(type: SubscriptionTypesNames):
    """Test get_type_id_by_name."""
    mocked_session = mock.AsyncMock()
    mocked_session.execute = mock.AsyncMock()
    mocked_session.execute.return_value.scalar_one_or_none = mock.Mock()
    mocked_session.execute.return_value.scalar_one_or_none.return_value = 1
    assert await get_type_id_by_name(mocked_session, type) == 1
    mocked_session.execute.assert_awaited_once()
    mocked_session.execute.return_value.scalar_one_or_none.assert_called_once_with()


@pytest.mark.asyncio
async def test_get_subscription_by_organization_id():
    """Test get_subscription_by_organization_id."""
    mocked_session = mock.AsyncMock()
    mocked_session.execute = mock.AsyncMock()
    mocked_session.execute.return_value.scalar_one_or_none = mock.Mock()
    mocked_session.execute.return_value.scalar_one_or_none.return_value = 1
    assert await get_subscription_by_organization_id(mocked_session, "dummy") == 1
    mocked_session.execute.assert_awaited_once()
    mocked_session.execute.return_value.scalar_one_or_none.assert_called_once_with()


@pytest.mark.asyncio
async def test_get_subscription_by_id():
    """Test get_subscription_by_id."""
    mocked_session = mock.AsyncMock()
    mocked_session.execute = mock.AsyncMock()
    mocked_session.execute.return_value.scalar_one_or_none = mock.Mock()
    mocked_session.execute.return_value.scalar_one_or_none.return_value = 1
    assert await get_subscription_by_id(mocked_session, 1) == 1
    mocked_session.execute.assert_awaited_once()
    mocked_session.execute.return_value.scalar_one_or_none.assert_called_once_with()


@pytest.mark.asyncio
async def test_get_pending_aws_subscription_by_organization_id():
    """Test get_pending_aws_subscription_by_organization_id."""
    mocked_session = mock.AsyncMock()
    mocked_session.execute = mock.AsyncMock()
    mocked_session.execute.return_value.scalar_one_or_none = mock.Mock()
    mocked_session.execute.return_value.scalar_one_or_none.return_value = 1
    assert await get_pending_aws_subscription_by_organization_id(mocked_session, "dummy") == 1
    mocked_session.execute.assert_awaited_once()
    mocked_session.execute.return_value.scalar_one_or_none.assert_called_once_with()
