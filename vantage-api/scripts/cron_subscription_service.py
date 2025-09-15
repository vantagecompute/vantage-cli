"""Core script for defining a cron scheduled service to handle subscriptions.

This script is responsible for the following actions:

1. Iterate over all non AWS subscriptions in all databases and delete
entries where the *expires_at* is before the current time;
2. Send a metered report to AWS regarding each AWS subscription.

Usage instructions (supposing you are in the root directory of the project):

```bash
poetry run python scripts/cron_subscription_service.py --help
```

```bash
poetry run python scripts/cron_subscription_service.py aws --help
```

```bash
poetry run python scripts/cron_subscription_service.py cloud --help
```
"""
# ignoring E402 because we need to run sys.path.append earlier
# ruff: noqa: E402
import asyncio
import enum
import os
import sys
from datetime import datetime, timezone
from typing import List, Type

# solve ModuleNotFoundError when importing stuff from the api module
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import typer
from loguru import logger
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Delete, Select, Update

from api.metering_mktplace_app.metering_mktplace_ops import get_metering_mkt_client
from api.routers.subscriptions.helpers import get_tier_id_by_name, get_type_id_by_name
from api.settings import SETTINGS
from api.sql_app.enums import (
    SubscriptionTierClusters,
    SubscriptionTierSeats,
    SubscriptionTiersNames,
    SubscriptionTierStorageSystems,
    SubscriptionTypesNames,
)
from api.sql_app.models import ClusterModel, StorageModel, SubscriptionModel
from api.sql_app.session import create_async_session
from api.utils.helpers import fetch_users_count


def _determine_tier(count: int, tiers: Type[enum.Enum]) -> enum.Enum:
    """Determine the tier based on the count and the tiers enum."""
    for tier in tiers:
        if count <= tier.value:
            return tier
    assert hasattr(tiers, "enterprise")
    return tiers.enterprise  # Assuming enterprise as the default highest tier


async def _fetch_all_database_names() -> List[str]:
    """Fetch all database names matching an uuid."""
    session = await create_async_session("postgres")
    async with session() as sess:
        query = r"SELECT datname FROM pg_database WHERE datname ~ '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$';"  # noqa: E501
        result = await sess.execute(text(query))
        database_names: list[str] = [row[0] for row in result.fetchall()]
        logger.info(f"Found {len(database_names)} databases: {database_names}")
        return database_names


async def _delete_expired_subscriptions(tenant: str) -> None:
    """Delete expired subscriptions for a given tenant."""
    session = await create_async_session(tenant)
    async with session() as sess:
        query: Select | Delete

        query = select(SubscriptionModel.id).filter(SubscriptionModel.expires_at < text("NOW()"))
        result = (await sess.execute(query)).fetchall()

        logger.info(f"Deleting {len(result)} expired subscriptions for tenant {tenant}")
        ids = [row[0] for row in result]
        query = delete(SubscriptionModel).where(SubscriptionModel.id.in_(ids))
        await sess.execute(query)
        await sess.commit()


async def _iterate_over_non_aws_subscriptions(database_names: list[str]) -> None:
    """Iterate over all non AWS subscriptions and delete expired ones."""
    for db_name in database_names:
        await _delete_expired_subscriptions(db_name)


async def _fetch_clusters_count(session: AsyncSession) -> int:
    """Fetch the number of clusters from the ClusterModel."""
    query = select(func.count()).select_from(ClusterModel)
    return (await session.execute(query)).scalar_one()


async def _fetch_storage_systems_count(session: AsyncSession) -> int:
    """Fetch the number of storage systems from the StorageModel."""
    query = select(func.count()).select_from(StorageModel)
    return (await session.execute(query)).scalar_one()


async def _calculate_aws_subscription_tier(tenant: str) -> str:
    """Calculate the AWS subscription tier for a given tenant."""
    session = await create_async_session(tenant)
    async with session() as sess:
        cluster_count = await _fetch_clusters_count(sess)
        storage_count = await _fetch_storage_systems_count(sess)
    user_count = await fetch_users_count(tenant)

    logger.info(
        f"Found the following counts for tenant {tenant}: "
        f"users={user_count}, clusters={cluster_count}, storage={storage_count}"
    )

    user_tier = _determine_tier(user_count, SubscriptionTierSeats)
    cluster_tier = _determine_tier(cluster_count, SubscriptionTierClusters)
    storage_tier = _determine_tier(storage_count, SubscriptionTierStorageSystems)

    logger.info(
        f"Calculated tiers for tenant {tenant}: user={user_tier}, "
        f"cluster={cluster_tier}, storage={storage_tier}"
    )

    if (
        user_tier == SubscriptionTierSeats.enterprise
        or cluster_tier == SubscriptionTierClusters.enterprise
        or storage_tier == SubscriptionTierStorageSystems.enterprise
    ):
        selected_tier = SubscriptionTiersNames.enterprise.value
    elif (
        user_tier == SubscriptionTierSeats.pro
        or cluster_tier == SubscriptionTierClusters.pro
        or storage_tier == SubscriptionTierStorageSystems.pro
    ):
        selected_tier = SubscriptionTiersNames.pro.value
    elif (
        user_tier == SubscriptionTierSeats.teams
        or cluster_tier == SubscriptionTierClusters.teams
        or storage_tier == SubscriptionTierStorageSystems.teams
    ):
        selected_tier = SubscriptionTiersNames.teams.value
    else:
        selected_tier = SubscriptionTiersNames.starter.value

    logger.info(f"Selected tier for tenant {tenant}: {selected_tier}")

    return selected_tier


async def _send_metered_report_to_aws(tenants: list[str]) -> None:
    """Send a metered report to AWS regarding a given tenant."""
    if len(tenants) == 0:
        logger.info("No AWS subscribed tenants found")
        return
    metering_mktplace_client = get_metering_mkt_client()
    response = metering_mktplace_client.batch_meter_usage(
        UsageRecords=[
            {
                "Timestamp": datetime.now(tz=timezone.utc),
                "CustomerIdentifier": (await _fetch_aws_customer_info(tenant))["customer_identifier"],
                "Dimension": await _calculate_aws_subscription_tier(tenant),
                "Quantity": await fetch_users_count(tenant),
            }
            for tenant in tenants
        ],
        ProductCode=SETTINGS.VANTAGE_PRODUCT_CODE,
    )
    logger.info(f"Sent metered report to AWS for {len(tenants)} tenants")
    logger.debug(response)


async def _is_tenant_aws_subscribed(tenant: str) -> bool:
    """Check if a tenant is AWS subscribed."""
    session = await create_async_session(tenant)
    async with session() as sess:
        aws_type_id = await get_type_id_by_name(sess, SubscriptionTypesNames.aws)
        query = select(SubscriptionModel.id).where(SubscriptionModel.type_id == aws_type_id)
        result = (await sess.execute(query)).fetchone()
        return result is not None


async def _fetch_aws_customer_info(tenant: str) -> dict[str, str]:
    """Fetch the AWS customer info for a given tenant."""
    session = await create_async_session(tenant)
    async with session() as sess:
        aws_type_id = await get_type_id_by_name(sess, SubscriptionTypesNames.aws)
        query = select(SubscriptionModel.detail_data).where(SubscriptionModel.type_id == aws_type_id)
        result = (await sess.execute(query)).fetchone()
        assert result is not None
        return result[0]


async def _set_aws_customer_tier(tenant: str, tier: str) -> None:
    """Set the AWS customer tier for a given tenant."""
    session = await create_async_session(tenant)
    async with session() as sess:
        query: Select | Update
        aws_type_id = await get_type_id_by_name(sess, SubscriptionTypesNames.aws)
        query = select(SubscriptionModel.id).where(SubscriptionModel.type_id == aws_type_id).with_for_update()
        subscription_id: int | None = (await sess.execute(query)).scalar_one_or_none()
        assert subscription_id is not None

        tier_id = await get_tier_id_by_name(sess, SubscriptionTiersNames(tier))

        query = (
            update(SubscriptionModel).where(SubscriptionModel.id == subscription_id).values(tier_id=tier_id)
        )
        await sess.execute(query)
        await sess.commit()


async def _update_aws_customers_tiers(tenants: list[str]) -> None:
    """Iterate over the tenants and update the tier of each one."""
    for tenant in tenants:
        tier = await _calculate_aws_subscription_tier(tenant)
        await _set_aws_customer_tier(tenant, tier)


async def _fetch_aws_subscribed_tenants(database_names: list[str]) -> list[str]:
    """Fetch the AWS subscribed tenants."""
    subscribed_tenants = []
    for db_name in database_names:
        if not await _is_tenant_aws_subscribed(db_name):
            continue
        subscribed_tenants.append(db_name)
    return subscribed_tenants


async def update_aws_customers_tiers() -> None:
    """Update AWS customers tiers."""
    database_names = await _fetch_all_database_names()
    subscribed_tenants = await _fetch_aws_subscribed_tenants(database_names)
    await _update_aws_customers_tiers(subscribed_tenants)


async def send_metered_report_to_aws() -> None:
    """Send a metered report to AWS."""
    database_names = await _fetch_all_database_names()
    subscribed_tenants = await _fetch_aws_subscribed_tenants(database_names)
    await _send_metered_report_to_aws(subscribed_tenants)


async def process_cloud_subscriptions() -> None:
    """Process cloud subscriptions."""
    database_names = await _fetch_all_database_names()
    await _iterate_over_non_aws_subscriptions(database_names)


app = typer.Typer()

cloud_subapp = typer.Typer()

aws_subapp = typer.Typer()

app.add_typer(cloud_subapp, name="cloud")
app.add_typer(aws_subapp, name="aws")


@cloud_subapp.command("process")
def process_cloud_subscriptions_command():
    """Process cloud subscriptions."""
    asyncio.run(process_cloud_subscriptions())


@aws_subapp.command("update-tiers")
def update_aws_customers_tiers_command():
    """Update AWS customers tiers."""
    asyncio.run(update_aws_customers_tiers())


@aws_subapp.command("send-metered-report")
def send_metered_report_to_aws_command():
    """Send a metered report to AWS."""
    asyncio.run(send_metered_report_to_aws())


if __name__ == "__main__":
    app()
