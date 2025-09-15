"""Helper functions for the subscriptions router."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import subqueryload

from api.settings import SETTINGS
from api.sql_app.models import (
    PendingAwsSubscriptionsModel,
    SubscriptionModel,
    SubscriptionTierModel,
    SubscriptionTypeModel,
)
from api.sql_app.schemas import SubscriptionTiersNames, SubscriptionTypesNames

subscription_tiers: dict[str, int] = {}
subscription_types: dict[str, int] = {}


async def get_tier_id_by_name(session: AsyncSession, name: SubscriptionTiersNames) -> int:
    """Get the tier id by name."""
    print(subscription_tiers)
    if name.name in subscription_tiers:
        return subscription_tiers[name.name]
    else:
        query = select(SubscriptionTierModel.id).where(SubscriptionTierModel.name == name)
        tier_id = (await session.execute(query)).scalar_one_or_none()
        assert isinstance(tier_id, int)
        if SETTINGS.TEST_ENV is False:
            subscription_tiers[name.name] = tier_id
        return tier_id


async def get_type_id_by_name(session: AsyncSession, name: SubscriptionTypesNames) -> int:
    """Get the type id by name."""
    if name.name in subscription_types:
        return subscription_types[name.name]
    else:
        query = select(SubscriptionTypeModel.id).where(SubscriptionTypeModel.name == name)
        type_id = (await session.execute(query)).scalar_one_or_none()
        assert isinstance(type_id, int)
        if SETTINGS.TEST_ENV is False:
            subscription_types[name.name] = type_id
        return type_id


async def get_subscription_by_organization_id(
    session: AsyncSession, organization_id: str
) -> SubscriptionModel | None:
    """Get a subscription by the organization id."""
    query = (
        select(SubscriptionModel)
        .options(
            subqueryload(SubscriptionModel.subscription_tier),
            subqueryload(SubscriptionModel.subscription_type),
        )
        .where(SubscriptionModel.organization_id == organization_id)
    )
    subscription = (await session.execute(query)).scalar_one_or_none()
    return subscription


async def get_subscription_by_id(session: AsyncSession, subscription_id: int) -> SubscriptionModel | None:
    """Get a subscription by the id."""
    query = (
        select(SubscriptionModel)
        .options(
            subqueryload(SubscriptionModel.subscription_tier),
            subqueryload(SubscriptionModel.subscription_type),
        )
        .where(SubscriptionModel.id == subscription_id)
    )
    subscription = (await session.execute(query)).scalar_one_or_none()
    return subscription


async def get_pending_aws_subscription_by_organization_id(
    session: AsyncSession, organization_id: str
) -> PendingAwsSubscriptionsModel | None:
    """Get a pending AWS subscription by the organization id."""
    query = select(PendingAwsSubscriptionsModel).where(
        PendingAwsSubscriptionsModel.organization_id == organization_id
    )
    subscription = (await session.execute(query)).scalar_one_or_none()
    return subscription
