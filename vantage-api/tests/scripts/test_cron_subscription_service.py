"""Core module for testing subscription service module."""
import enum
import math
from collections.abc import Callable
from datetime import datetime, timezone
from itertools import product
from typing import AsyncContextManager
from unittest import mock

import boto3
import pytest
from botocore.stub import Stubber
from freezegun import freeze_time
from freezegun.api import FakeDatetime  # type: ignore
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Insert, Select
from typer.testing import CliRunner

from api.settings import SETTINGS
from api.sql_app.enums import (
    CloudAccountEnum,
    ClusterProviderEnum,
    ClusterStatusEnum,
    StorageSourceEnum,
    SubscriptionTierClusters,
    SubscriptionTierSeats,
    SubscriptionTiersNames,
    SubscriptionTierStorageSystems,
    SubscriptionTypesNames,
)
from api.sql_app.models import (
    CloudAccountModel,
    ClusterModel,
    StorageModel,
    SubscriptionModel,
    SubscriptionTierModel,
    SubscriptionTypeModel,
)
from scripts.cron_subscription_service import (
    _calculate_aws_subscription_tier,
    _delete_expired_subscriptions,
    _determine_tier,
    _fetch_aws_customer_info,
    _fetch_aws_subscribed_tenants,
    _fetch_clusters_count,
    _fetch_storage_systems_count,
    _is_tenant_aws_subscribed,
    _iterate_over_non_aws_subscriptions,
    _send_metered_report_to_aws,
    _set_aws_customer_tier,
    _update_aws_customers_tiers,
    process_cloud_subscriptions,
    send_metered_report_to_aws,
    update_aws_customers_tiers,
)
from scripts.cron_subscription_service import app as cli_app


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tenant_info",
    [
        ({"tenant": "db1", "is_subscribed": True}, {"tenant": "db2", "is_subscribed": False}),
        ({"tenant": "db3", "is_subscribed": True}, {"tenant": "db4", "is_subscribed": True}),
        ({"tenant": "db5", "is_subscribed": False}, {"tenant": "db6", "is_subscribed": False}),
    ],
)
@mock.patch("scripts.cron_subscription_service._is_tenant_aws_subscribed")
async def test_fetch_aws_subscribed_tenants(
    mocked_is_tenant_aws_subscribed: mock.MagicMock,
    tenant_info: tuple[dict[str, str], dict[str, str]],
):
    """Verify if the expected functions are called when iterating over AWS subscriptions."""
    tenants = [tenant["tenant"] for tenant in tenant_info]
    subscribed_tenants = [tenant["tenant"] for tenant in tenant_info if tenant["is_subscribed"]]

    mocked_is_tenant_aws_subscribed.side_effect = [tenant["is_subscribed"] for tenant in tenant_info]

    result = await _fetch_aws_subscribed_tenants(tenants)

    assert result == subscribed_tenants
    mocked_is_tenant_aws_subscribed.assert_has_calls(calls=[mock.call(tenant) for tenant in tenants])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tenants",
    [
        [{"tenant": "alpha", "tier": "foo"}, {"tenant": "omega", "tier": "boo"}],
        [
            {"tenant": "chi", "tier": "baz"},
            {"tenant": "pi", "tier": "quux"},
            {"tenant": "lambda", "tier": "bar"},
        ],
        [{"tenant": "sigma", "tier": "eggs"}],
    ],
)
@mock.patch("scripts.cron_subscription_service._calculate_aws_subscription_tier")
@mock.patch("scripts.cron_subscription_service._set_aws_customer_tier")
async def test__update_aws_customers_tiers(
    mocked_set_aws_customer_tier: mock.MagicMock,
    mocked_calculate_aws_subscription_tier: mock.MagicMock,
    tenants: list[dict[str, str]],
):
    """Verify if the AWS customer tier is updated correctly."""
    mocked_calculate_aws_subscription_tier.side_effect = [tenant["tier"] for tenant in tenants]

    await _update_aws_customers_tiers([tenant["tenant"] for tenant in tenants])

    mocked_calculate_aws_subscription_tier.assert_has_calls(
        calls=[mock.call(tenant["tenant"]) for tenant in tenants]
    )
    mocked_set_aws_customer_tier.assert_has_calls(
        calls=[mock.call(tenant["tenant"], tenant["tier"]) for tenant in tenants]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "current_tier, upgrade_to_tier",
    list(product([x.value for x in SubscriptionTiersNames], repeat=2)),
)
async def test_set_aws_customer_tier__check_successful_change(
    current_tier: str,
    upgrade_to_tier: str,
    organization_id: str,
    get_session: Callable[[], AsyncContextManager[AsyncSession]],
    clean_up_database: None,
):
    """Verify if the function that modifies the AWS customer tier in the database operates correctly."""
    query: Insert | Select

    async with get_session() as sess:
        query = select(SubscriptionTypeModel.id).where(
            SubscriptionTypeModel.name == SubscriptionTypesNames.aws
        )
        type_id: int | None = (await sess.execute(query)).scalar()
        assert type_id is not None

        query = select(SubscriptionTierModel.id).where(SubscriptionTierModel.name == current_tier)
        tier_id: int | None = (await sess.execute(query)).scalar()
        assert tier_id is not None

        query = (
            insert(SubscriptionModel)
            .values(
                {
                    "organization_id": organization_id,
                    "type_id": type_id,
                    "tier_id": tier_id,
                    "detail_data": {"dummy": "foo"},
                    "is_free_trial": False,
                }
            )
            .returning(SubscriptionModel.id)
        )
        subscription_id: int | None = (await sess.execute(query)).scalar()
        assert subscription_id is not None
        await sess.commit()

    await _set_aws_customer_tier(organization_id, upgrade_to_tier)

    async with get_session() as sess:
        query = select(SubscriptionModel).where(SubscriptionModel.id == subscription_id)
        subscription: SubscriptionModel | None = (await sess.execute(query)).scalar_one_or_none()
        assert subscription is not None

        query = select(SubscriptionTierModel).where(SubscriptionTierModel.id == subscription.tier_id)
        expected_tier: SubscriptionTierModel | None = (await sess.execute(query)).scalar_one_or_none()
        assert expected_tier is not None

        assert expected_tier.name == upgrade_to_tier
        assert subscription.organization_id == organization_id
        assert subscription.type_id == type_id
        assert subscription.detail_data == {"dummy": "foo"}
        assert subscription.is_free_trial is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "detail_data, tier",
    [
        ({"customer_identifier": "123456789"}, SubscriptionTiersNames.starter),
        ({"customer_identifier": "987654321"}, SubscriptionTiersNames.teams),
        ({"customer_identifier": "1234567890"}, SubscriptionTiersNames.pro),
        ({"customer_identifier": "0987654321"}, SubscriptionTiersNames.enterprise),
    ],
)
async def test_fetch_aws_customer_info(
    detail_data: dict[str, str],
    tier: str,
    organization_id: str,
    get_session: Callable[[], AsyncContextManager[AsyncSession]],
    clean_up_database: None,
):
    """Verify if the AWS customer info is fetched correctly."""
    query: Insert | Select

    async with get_session() as sess:
        query = select(SubscriptionTypeModel.id).where(
            SubscriptionTypeModel.name == SubscriptionTypesNames.aws
        )
        type_id: int | None = (await sess.execute(query)).scalar()
        assert type_id is not None

        query = select(SubscriptionTierModel.id).where(SubscriptionTierModel.name == tier)
        tier_id: int | None = (await sess.execute(query)).scalar()
        assert tier_id is not None

        query = (
            insert(SubscriptionModel)
            .values(
                {
                    "organization_id": organization_id,
                    "type_id": type_id,
                    "tier_id": tier_id,
                    "detail_data": detail_data,
                    "is_free_trial": False,
                }
            )
            .returning(SubscriptionModel.id)
        )
        subscription_id: int | None = (await sess.execute(query)).scalar()
        assert subscription_id is not None
        await sess.commit()

    result = await _fetch_aws_customer_info(organization_id)

    assert result == detail_data

    # make sure the function didn't modify anything
    async with get_session() as sess:
        query = select(SubscriptionModel).where(SubscriptionModel.id == subscription_id)
        subcription: SubscriptionModel | None = (await sess.execute(query)).scalar_one_or_none()
        assert subcription is not None

        assert subcription.organization_id == organization_id
        assert subcription.type_id == type_id
        assert subcription.tier_id == tier_id
        assert subcription.detail_data == detail_data
        assert subcription.is_free_trial is False


@pytest.mark.asyncio
async def test_is_tenant_aws_subscribed__tenant_is_subscribed(
    organization_id: str,
    get_session: Callable[[], AsyncContextManager[AsyncSession]],
    clean_up_database: None,
):
    """Verify if the _is_tenant_aws_subscribed performs correctly when customer is subscribed."""
    query: Insert | Select

    async with get_session() as sess:
        query = select(SubscriptionTypeModel.id).where(
            SubscriptionTypeModel.name == SubscriptionTypesNames.aws
        )
        type_id: int | None = (await sess.execute(query)).scalar()
        assert type_id is not None

        query = select(SubscriptionTierModel.id).where(
            SubscriptionTierModel.name == SubscriptionTiersNames.starter
        )
        tier_id: int | None = (await sess.execute(query)).scalar()
        assert tier_id is not None

        query = (
            insert(SubscriptionModel)
            .values(
                {
                    "organization_id": organization_id,
                    "type_id": type_id,
                    "tier_id": tier_id,
                    "detail_data": {"dummy": "foo"},
                    "is_free_trial": False,
                }
            )
            .returning(SubscriptionModel.id)
        )
        subscription_id: int | None = (await sess.execute(query)).scalar()
        assert subscription_id is not None
        await sess.commit()

    is_subscribed = await _is_tenant_aws_subscribed(organization_id)

    assert is_subscribed is True


@pytest.mark.asyncio
async def test_is_tenant_aws_subscribed__tenant_is_not_subscribed(
    organization_id: str,
):
    """Verify if the _is_tenant_aws_subscribed performs correctly when customer isn't subscribed."""
    is_subscribed = await _is_tenant_aws_subscribed(organization_id)
    assert is_subscribed is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tenants",
    [
        [
            {
                "tenant": "alpha",
                "customer_identifier": "foo",
                "tier": SubscriptionTiersNames.starter.value,
                "users": 5,
            },
            {
                "tenant": "omega",
                "customer_identifier": "bar",
                "tier": SubscriptionTiersNames.pro.value,
                "users": 31,
            },
        ],
        [
            {
                "tenant": "chi",
                "customer_identifier": "baz",
                "tier": SubscriptionTiersNames.pro.value,
                "users": 29,
            },
            {
                "tenant": "pi",
                "customer_identifier": "boom",
                "tier": SubscriptionTiersNames.enterprise.value,
                "users": 119,
            },
            {
                "tenant": "lambda",
                "customer_identifier": "quux",
                "tier": SubscriptionTiersNames.teams.value,
                "users": 11,
            },
        ],
        [
            {
                "tenant": "sigma",
                "customer_identifier": "eggs",
                "tier": SubscriptionTiersNames.teams.value,
                "users": 20,
            }
        ],
    ],
)
@mock.patch("scripts.cron_subscription_service.get_metering_mkt_client")
@mock.patch("scripts.cron_subscription_service._fetch_aws_customer_info")
@mock.patch("scripts.cron_subscription_service._calculate_aws_subscription_tier")
@mock.patch("scripts.cron_subscription_service.fetch_users_count")
async def test__send_metered_report_to_aws(
    mocked_fetch_users_count: mock.MagicMock,
    mocked_calculate_aws_subscription_tier: mock.MagicMock,
    mocked_fetch_aws_customer_info: mock.MagicMock,
    mocked_get_metering_mkt_client: mock.MagicMock,
    tenants: list[dict[str, str]],
):
    """Verify if the metered report is sent to AWS correctly."""
    mocked_fetch_users_count.side_effect = [tenant["users"] for tenant in tenants]
    mocked_calculate_aws_subscription_tier.side_effect = [tenant["tier"] for tenant in tenants]
    mocked_fetch_aws_customer_info.side_effect = [
        {"customer_identifier": tenant["customer_identifier"]} for tenant in tenants
    ]

    metering_client = boto3.client("meteringmarketplace")
    stubber = Stubber(metering_client)
    stubber_response = {
        "Results": [
            {
                "UsageRecord": {
                    "CustomerIdentifier": tenant["customer_identifier"],
                    "Timestamp": datetime(2022, 1, 1, tzinfo=timezone.utc),
                    "Dimension": tenant["tier"],
                    "Quantity": tenant["users"],
                },
                "Status": "Success",
            }
            for tenant in tenants
        ]
    }
    stubber_params = {
        "UsageRecords": [
            {
                "CustomerIdentifier": tenant["customer_identifier"],
                "Timestamp": FakeDatetime(2022, 1, 1, tzinfo=timezone.utc),
                "Dimension": tenant["tier"],
                "Quantity": tenant["users"],
            }
            for tenant in tenants
        ],
        "ProductCode": SETTINGS.VANTAGE_PRODUCT_CODE,
    }
    stubber.add_response("batch_meter_usage", stubber_response, stubber_params)

    mocked_get_metering_mkt_client.return_value = metering_client

    with stubber, freeze_time("2022-01-01"):
        await _send_metered_report_to_aws([tenant["tenant"] for tenant in tenants])

    mocked_get_metering_mkt_client.assert_called_once_with()
    mocked_fetch_users_count.assert_has_calls(calls=[mock.call(tenant["tenant"]) for tenant in tenants])
    mocked_calculate_aws_subscription_tier.assert_has_calls(
        calls=[mock.call(tenant["tenant"]) for tenant in tenants]
    )
    mocked_fetch_aws_customer_info.assert_has_calls(calls=[mock.call(tenant["tenant"]) for tenant in tenants])


@pytest.mark.asyncio
@mock.patch("scripts.cron_subscription_service.get_metering_mkt_client")
@mock.patch("scripts.cron_subscription_service._fetch_aws_customer_info")
@mock.patch("scripts.cron_subscription_service._calculate_aws_subscription_tier")
@mock.patch("scripts.cron_subscription_service.fetch_users_count")
async def test__send_metered_report_to_aws__no_customer_for_reporting(
    mocked_fetch_users_count: mock.MagicMock,
    mocked_calculate_aws_subscription_tier: mock.MagicMock,
    mocked_fetch_aws_customer_info: mock.MagicMock,
    mocked_get_metering_mkt_client: mock.MagicMock,
):
    """Verify if the metered report is not sent to AWS when there's no customer to report about."""
    await _send_metered_report_to_aws([])

    mocked_get_metering_mkt_client.assert_not_called()
    mocked_fetch_users_count.assert_not_called()
    mocked_calculate_aws_subscription_tier.assert_not_called()
    mocked_fetch_aws_customer_info.assert_not_called()


@pytest.mark.parametrize(
    "tier_enum, count, expected",
    [
        # SubscriptionTierSeats cases
        (SubscriptionTierSeats, 1, SubscriptionTierSeats.starter),
        (SubscriptionTierSeats, 5, SubscriptionTierSeats.starter),
        (SubscriptionTierSeats, 6, SubscriptionTierSeats.teams),
        (SubscriptionTierSeats, 20, SubscriptionTierSeats.teams),
        (SubscriptionTierSeats, 21, SubscriptionTierSeats.pro),
        (SubscriptionTierSeats, 50, SubscriptionTierSeats.pro),
        (SubscriptionTierSeats, 51, SubscriptionTierSeats.enterprise),
        (SubscriptionTierSeats, 100, SubscriptionTierSeats.enterprise),
        (SubscriptionTierSeats, math.inf, SubscriptionTierSeats.enterprise),
        # SubscriptionTierClusters cases
        (SubscriptionTierClusters, 1, SubscriptionTierClusters.starter),
        (SubscriptionTierClusters, 2, SubscriptionTierClusters.starter),
        (SubscriptionTierClusters, 3, SubscriptionTierClusters.teams),
        (SubscriptionTierClusters, 10, SubscriptionTierClusters.teams),
        (SubscriptionTierClusters, 11, SubscriptionTierClusters.pro),
        (SubscriptionTierClusters, 20, SubscriptionTierClusters.pro),
        (SubscriptionTierClusters, 21, SubscriptionTierClusters.enterprise),
        (SubscriptionTierClusters, 50, SubscriptionTierClusters.enterprise),
        (SubscriptionTierClusters, math.inf, SubscriptionTierClusters.enterprise),
        # SubscriptionTierStorageSystems cases
        (SubscriptionTierStorageSystems, 1, SubscriptionTierStorageSystems.starter),
        (SubscriptionTierStorageSystems, 2, SubscriptionTierStorageSystems.starter),
        (SubscriptionTierStorageSystems, 3, SubscriptionTierStorageSystems.teams),
        (SubscriptionTierStorageSystems, 10, SubscriptionTierStorageSystems.teams),
        (SubscriptionTierStorageSystems, 11, SubscriptionTierStorageSystems.pro),
        (SubscriptionTierStorageSystems, 20, SubscriptionTierStorageSystems.pro),
        (SubscriptionTierStorageSystems, 21, SubscriptionTierStorageSystems.enterprise),
        (SubscriptionTierStorageSystems, 50, SubscriptionTierStorageSystems.enterprise),
        (SubscriptionTierStorageSystems, math.inf, SubscriptionTierStorageSystems.enterprise),
    ],
)
def test_determine_tier(tier_enum, count, expected):
    """Verify if the correct tier is determined based on the count."""
    assert _determine_tier(count, tier_enum) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "user_info, cluster_info, storage_info, expected_tier",
    [
        (
            {"count": 2, "tier": SubscriptionTierSeats.starter},
            {"count": 2, "tier": SubscriptionTierClusters.starter},
            {"count": 1, "tier": SubscriptionTierStorageSystems.starter},
            SubscriptionTiersNames.starter.value,
        ),
        (
            {"count": 4, "tier": SubscriptionTierSeats.starter},
            {"count": 8, "tier": SubscriptionTierClusters.teams},
            {"count": 6, "tier": SubscriptionTierStorageSystems.teams},
            SubscriptionTiersNames.teams.value,
        ),
        (
            {"count": 45, "tier": SubscriptionTierSeats.pro},
            {"count": 1, "tier": SubscriptionTierClusters.starter},
            {"count": 9, "tier": SubscriptionTierStorageSystems.teams},
            SubscriptionTiersNames.pro.value,
        ),
        (
            {"count": 46, "tier": SubscriptionTierSeats.pro},
            {"count": 36, "tier": SubscriptionTierClusters.enterprise},
            {"count": 1, "tier": SubscriptionTierStorageSystems.starter},
            SubscriptionTiersNames.enterprise.value,
        ),
    ],
)
@mock.patch("scripts.cron_subscription_service.fetch_users_count", new_callable=mock.AsyncMock)
@mock.patch("scripts.cron_subscription_service._fetch_storage_systems_count", new_callable=mock.AsyncMock)
@mock.patch("scripts.cron_subscription_service._fetch_clusters_count", new_callable=mock.AsyncMock)
@mock.patch("scripts.cron_subscription_service._determine_tier", new_callable=mock.Mock)
async def test_calculate_aws_subscription_tier(
    mocked_determine_tier: mock.Mock,
    mocked_fetch_clusters_count: mock.AsyncMock,
    mocked_fetch_storage_count: mock.AsyncMock,
    mocked_fetch_users_count: mock.AsyncMock,
    user_info: dict[str, int | enum.Enum],
    cluster_info: dict[str, int | enum.Enum],
    storage_info: dict[str, int | enum.Enum],
    expected_tier: str,
    organization_id: str,
):
    """Verify if the AWS subscription tier is calculated correctly."""
    mocked_fetch_users_count.return_value = user_info["count"]
    mocked_fetch_clusters_count.return_value = cluster_info["count"]
    mocked_fetch_storage_count.return_value = storage_info["count"]
    mocked_determine_tier.side_effect = [user_info["tier"], cluster_info["tier"], storage_info["tier"]]

    calculated_tier = await _calculate_aws_subscription_tier(organization_id)

    assert calculated_tier == expected_tier
    mocked_fetch_users_count.assert_called_once_with(organization_id)
    mocked_fetch_clusters_count.assert_called_once()
    mocked_fetch_storage_count.assert_called_once()
    mocked_determine_tier.assert_has_calls(
        calls=[
            mock.call(user_info["count"], SubscriptionTierSeats),
            mock.call(cluster_info["count"], SubscriptionTierClusters),
            mock.call(storage_info["count"], SubscriptionTierStorageSystems),
        ]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tenants",
    [
        ["db1", "db2", "db3"],
        ["db4", "db5"],
        ["db7"],
        [],
    ],
)
@mock.patch("scripts.cron_subscription_service._delete_expired_subscriptions", new_callable=mock.AsyncMock)
async def test_iterate_over_non_aws_subscriptions(
    mocked_delete_expired_subscriptions: mock.AsyncMock, tenants: list[str]
):
    """Verify if the non-AWS subscriptions are iterated over correctly."""
    await _iterate_over_non_aws_subscriptions(tenants)
    mocked_delete_expired_subscriptions.assert_has_awaits(calls=[mock.call(tenant) for tenant in tenants])


@pytest.mark.asyncio
async def test_delete_expired_subscriptions__no_expired_subscriptions(
    organization_id: str,
    get_session: Callable[[], AsyncContextManager[AsyncSession]],
    clean_up_database: None,
):
    """Verify if no subscription is deleted when calling _delete_expired_subscriptions."""
    query: Select | Insert
    async with get_session() as sess:
        query = insert(SubscriptionModel).values(
            {
                "organization_id": organization_id,
                "type_id": 1,
                "tier_id": 1,
                "detail_data": {"dummy": "foo"},
                "is_free_trial": False,
            }
        )
        await sess.execute(query)
        await sess.commit()

    await _delete_expired_subscriptions(organization_id)

    async with get_session() as sess:
        query = select(SubscriptionModel).where(SubscriptionModel.organization_id == organization_id)
        subscriptions: list[SubscriptionModel] = (await sess.execute(query)).scalars().all()
        assert len(subscriptions) == 1


@pytest.mark.asyncio
async def test_delete_expired_subscriptions__expired_subscriptions(
    organization_id: str,
    get_session: Callable[[], AsyncContextManager[AsyncSession]],
    clean_up_database: None,
):
    """Verify if the expired subscriptions are deleted correctly."""
    query: Select | Insert
    async with get_session() as sess:
        query = insert(SubscriptionModel).values(
            {
                "organization_id": organization_id,
                "type_id": 1,
                "tier_id": 1,
                "detail_data": {"dummy": "foo"},
                "is_free_trial": False,
                "expires_at": datetime(2021, 1, 1, tzinfo=timezone.utc),
            }
        )
        await sess.execute(query)
        await sess.commit()

    await _delete_expired_subscriptions(organization_id)

    async with get_session() as sess:
        query = select(SubscriptionModel).where(SubscriptionModel.organization_id == organization_id)
        subscriptions: list[SubscriptionModel] = (await sess.execute(query)).scalars().all()
        assert len(subscriptions) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "number_of_clusters",
    [3, 7, 10, 21, 1],
)
async def test_fetch_clusters_count(
    number_of_clusters: int,
    get_session: Callable[[], AsyncContextManager[AsyncSession]],
    clean_up_database: None,
):
    """Verify if the clusters count is fetched correctly."""
    async with get_session() as sess:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "provider": CloudAccountEnum.aws,
                    "attributes": {"dummy": "foo"},
                    "description": "test",
                    "name": "test",
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()

        query = insert(ClusterModel).values(
            [
                {
                    "name": f"cluster_{i}",
                    "provider": ClusterProviderEnum.aws,
                    "status": ClusterStatusEnum.ready,
                    "cloud_account_id": cloud_account_id,
                    "owner_email": "foo@gmail.com",
                    "client_id": "123",
                    "creation_parameters": {"dummy": "foo"},
                }
                for i in range(number_of_clusters)
            ]
        )
        await sess.execute(query)
        await sess.commit()

    async with get_session() as sess:
        count = await _fetch_clusters_count(sess)
    assert count == number_of_clusters


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "number_of_storage_systems",
    [4, 11, 1, 25, 43],
)
async def test_fetch_storage_systems_count(
    number_of_storage_systems: int,
    get_session: Callable[[], AsyncContextManager[AsyncSession]],
    clean_up_database: None,
):
    """Verify if the storage systems count is fetched correctly."""
    async with get_session() as sess:
        query = (
            insert(CloudAccountModel)
            .values(
                {
                    "provider": CloudAccountEnum.aws,
                    "attributes": {"dummy": "foo"},
                    "description": "test",
                    "name": "test",
                }
            )
            .returning(CloudAccountModel.id)
        )
        cloud_account_id = (await sess.execute(query)).scalar()

        query = insert(StorageModel).values(
            [
                {
                    "fs_id": f"fs_{i}",
                    "name": f"storage_{i}",
                    "region": "us-east-1",
                    "source": StorageSourceEnum.imported,
                    "owner": "foo@gmail.com",
                    "cloud_account_id": cloud_account_id,
                }
                for i in range(number_of_storage_systems)
            ]
        )
        await sess.execute(query)
        await sess.commit()

    async with get_session() as sess:
        count = await _fetch_storage_systems_count(sess)
    assert count == number_of_storage_systems


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "database_names, subscribed_tenants",
    [
        (["db1", "db2", "db3"], ["db1", "db3"]),
        (["db4", "db5"], ["db4", "db5"]),
        (["db7"], []),
        ([], []),
    ],
)
@mock.patch("scripts.cron_subscription_service._fetch_all_database_names", new_callable=mock.AsyncMock)
@mock.patch("scripts.cron_subscription_service._fetch_aws_subscribed_tenants", new_callable=mock.AsyncMock)
@mock.patch("scripts.cron_subscription_service._update_aws_customers_tiers", new_callable=mock.AsyncMock)
async def test_update_aws_customers_tiers(
    mocked_update_aws_customers_tiers: mock.AsyncMock,
    mocked_fetch_aws_subscribed_tenants: mock.AsyncMock,
    mocked_fetch_all_database_names: mock.AsyncMock,
    database_names: list[str],
    subscribed_tenants: list[str],
):
    """Verify if the update_aws_customers_tiers function behaves correctly."""
    mocked_fetch_all_database_names.return_value = database_names
    mocked_fetch_aws_subscribed_tenants.return_value = subscribed_tenants
    await update_aws_customers_tiers()
    mocked_fetch_all_database_names.assert_awaited_once_with()
    mocked_fetch_aws_subscribed_tenants.assert_awaited_once_with(database_names)
    mocked_update_aws_customers_tiers.assert_awaited_once_with(subscribed_tenants)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "database_names, subscribed_tenants",
    [
        (["db1", "db2", "db3"], ["db1", "db3"]),
        (["db4", "db5"], ["db4", "db5"]),
        (["db7"], []),
        ([], []),
    ],
)
@mock.patch("scripts.cron_subscription_service._fetch_all_database_names", new_callable=mock.AsyncMock)
@mock.patch("scripts.cron_subscription_service._fetch_aws_subscribed_tenants", new_callable=mock.AsyncMock)
@mock.patch("scripts.cron_subscription_service._send_metered_report_to_aws", new_callable=mock.AsyncMock)
async def test_send_metered_report_to_aws(
    mocked_send_metered_report_to_aws: mock.AsyncMock,
    mocked_fetch_aws_subscribed_tenants: mock.AsyncMock,
    mocked_fetch_all_database_names: mock.AsyncMock,
    database_names: list[str],
    subscribed_tenants: list[str],
):
    """Verify if the send_metered_report_to_aws function behaves correctly."""
    mocked_fetch_all_database_names.return_value = database_names
    mocked_fetch_aws_subscribed_tenants.return_value = subscribed_tenants
    await send_metered_report_to_aws()
    mocked_fetch_all_database_names.assert_awaited_once_with()
    mocked_fetch_aws_subscribed_tenants.assert_awaited_once_with(database_names)
    mocked_send_metered_report_to_aws.assert_awaited_once_with(subscribed_tenants)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "database_names",
    [
        ["db1", "db2", "db3"],
        ["db4", "db5"],
        ["db7"],
        [],
    ],
)
@mock.patch("scripts.cron_subscription_service._fetch_all_database_names", new_callable=mock.AsyncMock)
@mock.patch(
    "scripts.cron_subscription_service._iterate_over_non_aws_subscriptions", new_callable=mock.AsyncMock
)
async def test_process_cloud_subscriptions(
    mocked_iterate_over_non_aws_subscriptions: mock.AsyncMock,
    mocked_fetch_all_database_names: mock.AsyncMock,
    database_names: list[str],
):
    """Verify if the process_cloud_subscriptions function behaves correctly."""
    mocked_fetch_all_database_names.return_value = database_names
    await process_cloud_subscriptions()
    mocked_fetch_all_database_names.assert_awaited_once_with()
    mocked_iterate_over_non_aws_subscriptions.assert_awaited_once_with(database_names)


@mock.patch("scripts.cron_subscription_service.process_cloud_subscriptions")
@mock.patch("scripts.cron_subscription_service.asyncio.run")
def test_cli_app__process_cloud_subscriptions_command(
    mocked_asyncio_run: mock.MagicMock, mocked_process_cloud_subscriptions: mock.MagicMock
):
    """Verify if the process_cloud_subscriptions command behaves correctly."""
    mocked_process_cloud_subscriptions.return_value = mock.ANY
    runner = CliRunner()
    result = runner.invoke(cli_app, ["cloud", "process"])
    assert result.exit_code == 0
    mocked_asyncio_run.assert_called_once_with(mocked_process_cloud_subscriptions.return_value)


@mock.patch("scripts.cron_subscription_service.update_aws_customers_tiers_command")
@mock.patch("scripts.cron_subscription_service.asyncio.run")
def test_cli_app__update_aws_customers_tiers_command(
    mocked_asyncio_run: mock.MagicMock, mocked_update_aws_customers_tiers_command: mock.MagicMock
):
    """Verify if the process_cloud_subscriptions command behaves correctly."""
    mocked_update_aws_customers_tiers_command.return_value = mock.ANY
    runner = CliRunner()
    result = runner.invoke(cli_app, ["aws", "update-tiers"])
    assert result.exit_code == 0
    mocked_asyncio_run.assert_called_once_with(mocked_update_aws_customers_tiers_command())


@mock.patch("scripts.cron_subscription_service.send_metered_report_to_aws_command")
@mock.patch("scripts.cron_subscription_service.asyncio.run")
def test_cli_app__send_metered_report_to_aws_command(
    mocked_asyncio_run: mock.MagicMock, mocked_send_metered_report_to_aws_command: mock.MagicMock
):
    """Verify if the process_cloud_subscriptions command behaves correctly."""
    mocked_send_metered_report_to_aws_command.return_value = mock.ANY
    runner = CliRunner()
    result = runner.invoke(cli_app, ["aws", "send-metered-report"])
    assert result.exit_code == 0
    mocked_asyncio_run.assert_called_once_with(mocked_send_metered_report_to_aws_command())
