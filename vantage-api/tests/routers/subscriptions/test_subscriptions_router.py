"""Core module for testing the subscriptions router."""
import math
from collections.abc import AsyncGenerator, Callable
from datetime import datetime, timedelta, timezone
from itertools import product
from typing import AsyncContextManager
from unittest import mock

import botocore.session
import pytest
from botocore.stub import Stubber
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import Insert, Select

from api.body.output import (
    PendingAwsSubscriptionModel as PendingAwsSubscriptionModelOutput,
)
from api.body.output import (
    SubscriptionModel as SubscriptionModelOutput,
)
from api.sql_app.enums import (
    SubscriptionTierClusters,
    SubscriptionTierSeats,
    SubscriptionTiersNames,
    SubscriptionTierStorageSystems,
    SubscriptionTypesNames,
)
from api.sql_app.models import (
    OrganizationFreeTrialsModel,
    PendingAwsSubscriptionsModel,
    SubscriptionModel,
    SubscriptionTierModel,
    SubscriptionTypeModel,
)


@pytest.mark.asyncio
async def test_check_if_subscription_is_active__subscription_is_active(
    inject_security_header: Callable,
    test_client: AsyncClient,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
    organization_id: str,
):
    """Test the check_if_subscription_is_active endpoint with 200 HTTP code."""
    async with get_session() as sess:
        query: Select | Insert
        query = select(SubscriptionTierModel.id).where(
            SubscriptionTierModel.name == SubscriptionTiersNames.pro
        )
        tier_id = (await sess.execute(query)).scalars().first()

        query = select(SubscriptionTypeModel.id).where(
            SubscriptionTypeModel.name == SubscriptionTypesNames.aws
        )
        type_id = (await sess.execute(query)).scalars().first()

        query = insert(SubscriptionModel).values(
            organization_id=organization_id,
            type_id=type_id,
            tier_id=tier_id,
            detail_data={
                "product_code": "XA13VSDU926V",
                "customer_identifier": 123,
                "customer_aws_account_id": 201598653201,
            },
            expires_at=None,
        )
        await sess.execute(query)
        await sess.commit()

    inject_security_header("me", "admin:subscriptions:read")
    response = await test_client.get("/admin/management/subscriptions/my/is-active")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_check_if_subscription_is_active__subscription_is_expired(
    inject_security_header: Callable,
    test_client: AsyncClient,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
    organization_id: str,
):
    """Test the check_if_subscription_is_active endpoint with 402 HTTP code."""
    async with get_session() as sess:
        query: Select | Insert
        query = select(SubscriptionTierModel.id).where(
            SubscriptionTierModel.name == SubscriptionTiersNames.pro
        )
        tier_id = (await sess.execute(query)).scalars().first()

        query = select(SubscriptionTypeModel.id).where(
            SubscriptionTypeModel.name == SubscriptionTypesNames.aws
        )
        type_id = (await sess.execute(query)).scalars().first()

        query = insert(SubscriptionModel).values(
            organization_id=organization_id,
            type_id=type_id,
            tier_id=tier_id,
            detail_data={
                "product_code": "XA13VSDU926V",
                "customer_identifier": 123,
                "customer_aws_account_id": 201598653201,
            },
            expires_at=datetime.now(tz=timezone.utc) - timedelta(seconds=1),
        )
        await sess.execute(query)
        await sess.commit()

    inject_security_header("me", "admin:subscriptions:read")
    response = await test_client.get("/admin/management/subscriptions/my/is-active")
    assert response.status_code == 402


@pytest.mark.asyncio
async def test_check_if_subscription_is_active__subscription_does_not_exist(
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test the check_if_subscription_is_active endpoint with 404 HTTP code."""
    inject_security_header("me", "admin:subscriptions:read")
    response = await test_client.get("/admin/management/subscriptions/my/is-active")
    assert response.status_code == 404


@pytest.mark.asyncio
@mock.patch("api.routers.subscriptions.unpack_organization_id_from_token")
async def test_check_if_subscription_is_active__organization_not_in_token(
    mocked_unpack_organization_id_from_token: mock.MagicMock,
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test the check_if_subscription_is_active endpoint with 400 HTTP code."""
    mocked_unpack_organization_id_from_token.side_effect = AssertionError("Organization not found in token")

    inject_security_header("me", "admin:subscriptions:read")
    response = await test_client.get("/admin/management/subscriptions/my/is-active")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_organization_subscription__check_http_error_404(
    inject_security_header: Callable,
    test_client: AsyncClient,
    # get_session: AsyncGenerator[AsyncSession, None],
):
    """Test the get_organization_subscription endpoint with a 404 error."""
    inject_security_header("me", "admin:subscriptions:read")
    response = await test_client.get("/admin/management/subscriptions/my")

    assert response.status_code == 404
    assert response.json() == {"message": "No subscription found", "error": None}


@pytest.mark.asyncio
@mock.patch("api.routers.subscriptions.unpack_organization_id_from_token")
async def test_get_organization_subscription__check_http_error_400(
    mocked_unpack_organization_id_from_token: mock.MagicMock,
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test the get_organization_subscription endpoint with a 400 error."""
    mocked_unpack_organization_id_from_token.side_effect = AssertionError("Organization not found in token")

    inject_security_header("me", "admin:subscriptions:read")
    response = await test_client.get("/admin/management/subscriptions/my")

    assert response.status_code == 400
    assert response.json() == {"message": "Organization not found in token", "error": None}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "subscription_tier_name, subscription_type_name",
    list(product(SubscriptionTiersNames, SubscriptionTypesNames)),
)
async def test_get_organization_subscription__check_active_subscription__expires_at_is_none(
    subscription_tier_name: SubscriptionTiersNames,
    subscription_type_name: SubscriptionTypesNames,
    inject_security_header: Callable,
    test_client: AsyncClient,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
    organization_id: str,
):
    """Test the get_organization_subscription endpoint reports active for null expiration.

    This test verifies that a subscription is reaported as active when there
    is no expiration date supplied.
    """
    seats = getattr(SubscriptionTierSeats, subscription_tier_name.name)
    num_of_seats = None if seats.value == math.inf else int(seats.value)
    clusters = getattr(SubscriptionTierClusters, subscription_tier_name.name)
    num_of_clusters = None if clusters.value == math.inf else int(clusters.value)
    storage_systems = getattr(SubscriptionTierStorageSystems, subscription_tier_name.name)
    num_of_storage_systems = None if storage_systems.value == math.inf else int(storage_systems.value)

    query: Insert | Select
    async with get_session() as sess:
        query = select(SubscriptionTierModel.id).where(
            SubscriptionTierModel.name == subscription_tier_name.value
        )
        tier_id = (await sess.execute(query)).scalars().first()

        query = select(SubscriptionTypeModel.id).where(
            SubscriptionTypeModel.name == subscription_type_name.value
        )
        type_id = (await sess.execute(query)).scalars().first()

        query = (
            insert(SubscriptionModel)
            .values(
                organization_id=organization_id,
                type_id=type_id,
                tier_id=tier_id,
                detail_data={
                    "product_code": "XA13VSDU926V",
                    "customer_identifier": 123,
                    "customer_aws_account_id": 201598653201,
                },
                expires_at=None,
            )
            .returning(SubscriptionModel.id, SubscriptionModel.created_at)
        )
        subscription_id: int
        created_at: datetime
        subscription_id, created_at = (await sess.execute(query)).fetchone()

        await sess.commit()

    created_at_str = created_at.strftime("%Y-%m-%dT%H:%M:%S.%f%z")
    normalized_created_at = created_at_str[:-2] + ":" + created_at_str[-2:]

    inject_security_header("me", "admin:subscriptions:read")
    response = await test_client.get("/admin/management/subscriptions/my")

    assert response.status_code == 200
    assert response.json() == {
        "id": subscription_id,
        "organization_id": organization_id,
        "type_id": type_id,
        "tier_id": tier_id,
        "detail_data": {
            "product_code": "XA13VSDU926V",
            "customer_identifier": 123,
            "customer_aws_account_id": 201598653201,
        },
        "expires_at": None,
        "created_at": normalized_created_at,
        "subscription_type": {"id": type_id, "name": subscription_type_name.value},
        "subscription_tier": {
            "id": tier_id,
            "name": subscription_tier_name.value,
            "seats": num_of_seats,
            "clusters": num_of_clusters,
            "storage_systems": num_of_storage_systems,
        },
        "is_free_trial": False,
        "is_active": True,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "subscription_tier_name, subscription_type_name",
    list(product(SubscriptionTiersNames, SubscriptionTypesNames)),
)
async def test_get_organization_subscription__check_non_active_subscription__expires_at_is_not_none(
    subscription_tier_name: SubscriptionTiersNames,
    subscription_type_name: SubscriptionTypesNames,
    inject_security_header: Callable,
    test_client: AsyncClient,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
    organization_id: str,
):
    """Test the get_organization_subscription endpoint returns a non-active subscription when expires_at is set."""  # noqa: E501
    seats = getattr(SubscriptionTierSeats, subscription_tier_name.name)
    num_of_seats = None if seats.value == math.inf else int(seats.value)
    clusters = getattr(SubscriptionTierClusters, subscription_tier_name.name)
    num_of_clusters = None if clusters.value == math.inf else int(clusters.value)
    storage_systems = getattr(SubscriptionTierStorageSystems, subscription_tier_name.name)
    num_of_storage_systems = None if storage_systems.value == math.inf else int(storage_systems.value)
    expires_at = datetime.now(tz=timezone.utc) - timedelta(days=1)

    query: Insert | Select
    async with get_session() as sess:
        query = select(SubscriptionTierModel.id).where(
            SubscriptionTierModel.name == subscription_tier_name.value
        )
        tier_id = (await sess.execute(query)).scalars().first()

        query = select(SubscriptionTypeModel.id).where(
            SubscriptionTypeModel.name == subscription_type_name.value
        )
        type_id = (await sess.execute(query)).scalars().first()

        query = (
            insert(SubscriptionModel)
            .values(
                organization_id=organization_id,
                type_id=type_id,
                tier_id=tier_id,
                detail_data={
                    "product_code": "XA13VSDU926V",
                    "customer_identifier": 123,
                    "customer_aws_account_id": 201598653201,
                },
                expires_at=expires_at,
            )
            .returning(SubscriptionModel.id, SubscriptionModel.created_at)
        )
        subscription_id: int
        created_at: datetime
        subscription_id, created_at = (await sess.execute(query)).fetchone()

        await sess.commit()

    created_at_str = created_at.strftime("%Y-%m-%dT%H:%M:%S.%f%z")
    normalized_created_at = created_at_str[:-2] + ":" + created_at_str[-2:]

    expires_at_str = expires_at.strftime("%Y-%m-%dT%H:%M:%S.%f%z")
    normalized_expires_at = expires_at_str[:-2] + ":" + expires_at_str[-2:]

    inject_security_header("me", "admin:subscriptions:read")
    response = await test_client.get("/admin/management/subscriptions/my")

    assert response.status_code == 200
    assert response.json() == {
        "id": subscription_id,
        "organization_id": organization_id,
        "type_id": type_id,
        "tier_id": tier_id,
        "detail_data": {
            "product_code": "XA13VSDU926V",
            "customer_identifier": 123,
            "customer_aws_account_id": 201598653201,
        },
        "expires_at": normalized_expires_at,
        "created_at": normalized_created_at,
        "subscription_type": {"id": type_id, "name": subscription_type_name.value},
        "subscription_tier": {
            "id": tier_id,
            "name": subscription_tier_name.value,
            "seats": num_of_seats,
            "clusters": num_of_clusters,
            "storage_systems": num_of_storage_systems,
        },
        "is_free_trial": False,
        "is_active": False,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "subscription_tier_name, subscription_type_name",
    list(product(SubscriptionTiersNames, SubscriptionTypesNames)),
)
async def test_get_organization_subscription__check_active_subscription__expires_at_is_not_none(
    subscription_tier_name: SubscriptionTiersNames,
    subscription_type_name: SubscriptionTypesNames,
    inject_security_header: Callable,
    test_client: AsyncClient,
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
    organization_id: str,
):
    """Test the get_organization_subscription endpoint returns an active subscription when expires_at is set."""  # noqa: E501
    seats = getattr(SubscriptionTierSeats, subscription_tier_name.name)
    num_of_seats = None if seats.value == math.inf else int(seats.value)
    clusters = getattr(SubscriptionTierClusters, subscription_tier_name.name)
    num_of_clusters = None if clusters.value == math.inf else int(clusters.value)
    storage_systems = getattr(SubscriptionTierStorageSystems, subscription_tier_name.name)
    num_of_storage_systems = None if storage_systems.value == math.inf else int(storage_systems.value)
    expires_at = datetime.now(tz=timezone.utc) + timedelta(days=1)

    query: Insert | Select
    async with get_session() as sess:
        query = select(SubscriptionTierModel.id).where(
            SubscriptionTierModel.name == subscription_tier_name.value
        )
        tier_id = (await sess.execute(query)).scalars().first()

        query = select(SubscriptionTypeModel.id).where(
            SubscriptionTypeModel.name == subscription_type_name.value
        )
        type_id = (await sess.execute(query)).scalars().first()

        query = (
            insert(SubscriptionModel)
            .values(
                organization_id=organization_id,
                type_id=type_id,
                tier_id=tier_id,
                detail_data={
                    "product_code": "XA13VSDU926V",
                    "customer_identifier": 123,
                    "customer_aws_account_id": 201598653201,
                },
                expires_at=expires_at,
            )
            .returning(SubscriptionModel.id, SubscriptionModel.created_at)
        )
        subscription_id: int
        created_at: datetime
        subscription_id, created_at = (await sess.execute(query)).fetchone()

        await sess.commit()

    created_at_str = created_at.strftime("%Y-%m-%dT%H:%M:%S.%f%z")
    normalized_created_at = created_at_str[:-2] + ":" + created_at_str[-2:]

    expires_at_str = expires_at.strftime("%Y-%m-%dT%H:%M:%S.%f%z")
    normalized_expires_at = expires_at_str[:-2] + ":" + expires_at_str[-2:]

    inject_security_header("me", "admin:subscriptions:read")
    response = await test_client.get("/admin/management/subscriptions/my")

    assert response.status_code == 200
    assert response.json() == {
        "id": subscription_id,
        "organization_id": organization_id,
        "type_id": type_id,
        "tier_id": tier_id,
        "detail_data": {
            "product_code": "XA13VSDU926V",
            "customer_identifier": 123,
            "customer_aws_account_id": 201598653201,
        },
        "expires_at": normalized_expires_at,
        "created_at": normalized_created_at,
        "subscription_type": {"id": type_id, "name": subscription_type_name.value},
        "subscription_tier": {
            "id": tier_id,
            "name": subscription_tier_name.value,
            "seats": num_of_seats,
            "clusters": num_of_clusters,
            "storage_systems": num_of_storage_systems,
        },
        "is_free_trial": False,
        "is_active": True,
    }


@pytest.mark.asyncio
async def test_dummy_confirmation_endpoint__check_http_200(test_client: AsyncClient):
    """Test if the dummy confirmation endpoint is available when test env is true."""
    response = await test_client.get("/admin/management/subscriptions/aws-subscription/dummy-confirm")

    assert response.status_code == status.HTTP_200_OK
    assert response.text == "<h1>Subscription confirmed</hjson>"


@pytest.mark.asyncio
@mock.patch("api.routers.subscriptions.get_metering_mkt_client")
@pytest.mark.parametrize("x_amzn_marketplace_token", ["1234", "5678"])
async def test_initialize_aws_subscription__check_http_400__expired_token(
    mocked_get_metering_mkt_client: mock.MagicMock,
    x_amzn_marketplace_token: str,
    test_client: AsyncClient,
):
    """Test if the initialize_aws_subscription endpoint returns a 400 when the provided token has expired."""  # noqa: E501
    meteringmarketplace = botocore.session.get_session().create_client("meteringmarketplace")

    stubber = Stubber(meteringmarketplace)
    stubber.add_client_error(
        "resolve_customer",
        service_error_code="ExpiredTokenException",
        service_message="The token has expired",
        expected_params={"RegistrationToken": x_amzn_marketplace_token},
    )

    mocked_get_metering_mkt_client.return_value = meteringmarketplace

    with stubber:
        response = await test_client.post(
            "/admin/management/subscriptions/aws-subscription/initialize",
            data={"x-amzn-marketplace-token": x_amzn_marketplace_token},
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"message": "The token has expired", "error": "ExpiredTokenException"}
    mocked_get_metering_mkt_client.assert_called_once_with()


@pytest.mark.asyncio
@mock.patch("api.routers.subscriptions.get_metering_mkt_client")
@pytest.mark.parametrize("x_amzn_marketplace_token", ["1234", "5678"])
async def test_initialize_aws_subscription__check_http_400__internal_error(
    mocked_get_metering_mkt_client: mock.MagicMock,
    x_amzn_marketplace_token: str,
    test_client: AsyncClient,
):
    """Test if the initialize_aws_subscription endpoint returns a 400 when there's an internal error in the AWS API."""  # noqa: E501
    meteringmarketplace = botocore.session.get_session().create_client("meteringmarketplace")

    stubber = Stubber(meteringmarketplace)
    stubber.add_client_error(
        "resolve_customer",
        service_error_code="InternalServiceErrorException",
        service_message="Some weird internal error",
        expected_params={"RegistrationToken": x_amzn_marketplace_token},
    )

    mocked_get_metering_mkt_client.return_value = meteringmarketplace

    with stubber:
        response = await test_client.post(
            "/admin/management/subscriptions/aws-subscription/initialize",
            data={"x-amzn-marketplace-token": x_amzn_marketplace_token},
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "message": "An error occurred (InternalServiceErrorException) when calling the ResolveCustomer operation: Some weird internal error",  # noqa: E501
        "error": "InternalServiceErrorException",
    }
    mocked_get_metering_mkt_client.assert_called_once_with()


@pytest.mark.asyncio
@mock.patch("api.routers.subscriptions.get_metering_mkt_client")
@pytest.mark.parametrize("x_amzn_marketplace_token", ["1234", "5678"])
async def test_initialize_aws_subscription__check_http_400__token_is_invalid(
    mocked_get_metering_mkt_client: mock.MagicMock,
    x_amzn_marketplace_token: str,
    test_client: AsyncClient,
):
    """Test if the initialize_aws_subscription endpoint returns a 400 when the provided token is invalid."""
    meteringmarketplace = botocore.session.get_session().create_client("meteringmarketplace")

    stubber = Stubber(meteringmarketplace)
    stubber.add_client_error(
        "resolve_customer",
        service_error_code="InvalidTokenException",
        service_message="Token is invalid",
        expected_params={"RegistrationToken": x_amzn_marketplace_token},
    )

    mocked_get_metering_mkt_client.return_value = meteringmarketplace

    with stubber:
        response = await test_client.post(
            "/admin/management/subscriptions/aws-subscription/initialize",
            data={"x-amzn-marketplace-token": x_amzn_marketplace_token},
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"message": "The token is invalid", "error": "InvalidTokenException"}
    mocked_get_metering_mkt_client.assert_called_once_with()


@pytest.mark.asyncio
@mock.patch("api.routers.subscriptions.get_metering_mkt_client")
@pytest.mark.parametrize("x_amzn_marketplace_token", ["1234", "5678"])
async def test_initialize_aws_subscription__check_http_400__throttling_error(
    mocked_get_metering_mkt_client: mock.MagicMock,
    x_amzn_marketplace_token: str,
    test_client: AsyncClient,
):
    """Test if the initialize_aws_subscription endpoint returns a 400 when there's a throttling error on the AWS API."""  # noqa: E501
    meteringmarketplace = botocore.session.get_session().create_client("meteringmarketplace")

    stubber = Stubber(meteringmarketplace)
    stubber.add_client_error(
        "resolve_customer",
        service_error_code="ThrottlingException",
        service_message="Too many requests in the AWS API",
        expected_params={"RegistrationToken": x_amzn_marketplace_token},
    )

    mocked_get_metering_mkt_client.return_value = meteringmarketplace

    with stubber:
        response = await test_client.post(
            "/admin/management/subscriptions/aws-subscription/initialize",
            data={"x-amzn-marketplace-token": x_amzn_marketplace_token},
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"message": "Too many requests in the AWS API", "error": "ThrottlingException"}
    mocked_get_metering_mkt_client.assert_called_once_with()


@pytest.mark.asyncio
@mock.patch("api.routers.subscriptions.get_metering_mkt_client")
@pytest.mark.parametrize("x_amzn_marketplace_token", ["1234", "5678"])
async def test_initialize_aws_subscription__check_http_400__disabled_api(
    mocked_get_metering_mkt_client: mock.MagicMock,
    x_amzn_marketplace_token: str,
    test_client: AsyncClient,
):
    """Test if the initialize_aws_subscription endpoint returns a 400 when the AWS API is disabled."""
    meteringmarketplace = botocore.session.get_session().create_client("meteringmarketplace")

    stubber = Stubber(meteringmarketplace)
    stubber.add_client_error(
        "resolve_customer",
        service_error_code="DisabledApiException",
        service_message="API is disabled",
        expected_params={"RegistrationToken": x_amzn_marketplace_token},
    )

    mocked_get_metering_mkt_client.return_value = meteringmarketplace

    with stubber:
        response = await test_client.post(
            "/admin/management/subscriptions/aws-subscription/initialize",
            data={"x-amzn-marketplace-token": x_amzn_marketplace_token},
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"message": "The AWS API is disabled", "error": "DisabledApiException"}
    mocked_get_metering_mkt_client.assert_called_once_with()


@pytest.mark.asyncio
@mock.patch("api.routers.subscriptions.get_metering_mkt_client")
@pytest.mark.parametrize(
    "x_amzn_marketplace_token, product_code, customer_identifier, customer_aws_account_id",
    [
        ("1234", "XA13VSDU926V", "123", "123456789012"),
        ("5678", "BAKJH973MNDh", "321", "210987654321"),
    ],
)
async def test_initialize_aws_subscription__check_http_303__test_env_true(
    mocked_get_metering_mkt_client: mock.MagicMock,
    x_amzn_marketplace_token: str,
    product_code: str,
    customer_identifier: str,
    customer_aws_account_id: str,
    test_client: AsyncClient,
):
    """Test if the initialize_aws_subscription endpoint returns a 303 status code when test env is set to True."""  # noqa: E501
    meteringmarketplace = botocore.session.get_session().create_client("meteringmarketplace")

    stubber = Stubber(meteringmarketplace)
    stubber.add_response(
        "resolve_customer",
        {
            "ProductCode": product_code,
            "CustomerIdentifier": customer_identifier,
            "CustomerAWSAccountId": customer_aws_account_id,
        },
        {"RegistrationToken": x_amzn_marketplace_token},
    )

    mocked_get_metering_mkt_client.return_value = meteringmarketplace

    with stubber:
        response = await test_client.post(
            "/admin/management/subscriptions/aws-subscription/initialize",
            data={"x-amzn-marketplace-token": x_amzn_marketplace_token},
        )

    assert response.status_code == status.HTTP_303_SEE_OTHER
    assert (
        response.headers["location"]
        == "http://localhost:8080/admin/management/subscriptions/aws-subscription/dummy-confirm"
    )
    assert response.headers["set-cookie"] == (
        f"product_code={product_code}; Domain=localhost; Path=/; SameSite=lax, "
        f"customer_identifier={customer_identifier}; Domain=localhost; Path=/; SameSite=lax, "
        f"customer_aws_account_id={customer_aws_account_id}; Domain=localhost; Path=/; SameSite=lax"
    )
    mocked_get_metering_mkt_client.assert_called_once_with()


@pytest.mark.asyncio
@mock.patch("api.routers.subscriptions.get_metering_mkt_client")
@pytest.mark.parametrize(
    "x_amzn_marketplace_token, product_code, customer_identifier, customer_aws_account_id, app_domain",
    [
        ("1234", "XA13VSDU926V", "123", "123456789012", "example.com"),
        ("5678", "BAKJH973MNDh", "321", "210987654321", "example.org"),
    ],
)
async def test_initialize_aws_subscription__check_http_303__test_env_false__production_stage(
    mocked_get_metering_mkt_client: mock.MagicMock,
    x_amzn_marketplace_token: str,
    product_code: str,
    customer_identifier: str,
    customer_aws_account_id: str,
    app_domain: str,
    test_client: AsyncClient,
):
    """Test if the initialize_aws_subscription endpoint returns a 303 status code when test env is false and the stage is production."""  # noqa: E501
    meteringmarketplace = botocore.session.get_session().create_client("meteringmarketplace")

    stubber = Stubber(meteringmarketplace)
    stubber.add_response(
        "resolve_customer",
        {
            "ProductCode": product_code,
            "CustomerIdentifier": customer_identifier,
            "CustomerAWSAccountId": customer_aws_account_id,
        },
        {"RegistrationToken": x_amzn_marketplace_token},
    )

    mocked_get_metering_mkt_client.return_value = meteringmarketplace

    with stubber, mock.patch("api.routers.subscriptions.SETTINGS.APP_DOMAIN", app_domain), mock.patch(
        "api.routers.subscriptions.SETTINGS.STAGE", "production"
    ), mock.patch("api.routers.subscriptions.SETTINGS.TEST_ENV", False):
        response = await test_client.post(
            "/admin/management/subscriptions/aws-subscription/initialize",
            data={"x-amzn-marketplace-token": x_amzn_marketplace_token},
        )

    assert response.status_code == status.HTTP_303_SEE_OTHER
    assert response.headers["location"] == f"https://app.{app_domain}"
    assert response.headers["set-cookie"] == (
        f"product_code={product_code}; Domain={app_domain}; Path=/; SameSite=lax, "
        f"customer_identifier={customer_identifier}; Domain={app_domain}; Path=/; SameSite=lax, "
        f"customer_aws_account_id={customer_aws_account_id}; Domain={app_domain}; Path=/; SameSite=lax"
    )
    mocked_get_metering_mkt_client.assert_called_once_with()


@pytest.mark.asyncio
@mock.patch("api.routers.subscriptions.get_metering_mkt_client")
@pytest.mark.parametrize(
    "x_amzn_marketplace_token, product_code, customer_identifier, customer_aws_account_id, app_domain, stage",
    [
        ("1234", "XA13VSDU926V", "123", "123456789012", "example.com", "staging"),
        ("5678", "BAKJH973MNDh", "321", "210987654321", "example.org", "development"),
    ],
)
async def test_initialize_aws_subscription__check_http_303__test_env_false__dummy_stage(
    mocked_get_metering_mkt_client: mock.MagicMock,
    x_amzn_marketplace_token: str,
    product_code: str,
    customer_identifier: str,
    customer_aws_account_id: str,
    app_domain: str,
    stage: str,
    test_client: AsyncClient,
):
    """Test if the initialize_aws_subscription endpoint returns a 303 status code when test env is false and the stage is a dummy value."""  # noqa: E501
    meteringmarketplace = botocore.session.get_session().create_client("meteringmarketplace")

    stubber = Stubber(meteringmarketplace)
    stubber.add_response(
        "resolve_customer",
        {
            "ProductCode": product_code,
            "CustomerIdentifier": customer_identifier,
            "CustomerAWSAccountId": customer_aws_account_id,
        },
        {"RegistrationToken": x_amzn_marketplace_token},
    )

    mocked_get_metering_mkt_client.return_value = meteringmarketplace

    with stubber, mock.patch("api.routers.subscriptions.SETTINGS.APP_DOMAIN", app_domain), mock.patch(
        "api.routers.subscriptions.SETTINGS.STAGE", stage
    ), mock.patch("api.routers.subscriptions.SETTINGS.TEST_ENV", False):
        response = await test_client.post(
            "/admin/management/subscriptions/aws-subscription/initialize",
            data={"x-amzn-marketplace-token": x_amzn_marketplace_token},
        )

    assert response.status_code == status.HTTP_303_SEE_OTHER
    assert response.headers["location"] == f"https://app.{stage}.{app_domain}"
    assert response.headers["set-cookie"] == (
        f"product_code={product_code}; Domain={app_domain}; Path=/; SameSite=lax, "
        f"customer_identifier={customer_identifier}; Domain={app_domain}; Path=/; SameSite=lax, "
        f"customer_aws_account_id={customer_aws_account_id}; Domain={app_domain}; Path=/; SameSite=lax"
    )
    mocked_get_metering_mkt_client.assert_called_once_with()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "product_code, customer_identifier, customer_aws_account_id",
    [
        ("XA13VSDU926V", "123", "123456789012"),
        ("BAKJH973MNDh", "321", "210987654321"),
        ("eyothuq1lx973s1i7i7vpsbrp", "321", "210987654321"),
        ("prbspv7i7i1s379xl1quhtoye", "321", "210987654321"),
    ],
)
async def test_finalize_aws_subscription__check_http_409(
    product_code: str,
    customer_identifier: str,
    customer_aws_account_id: str,
    test_client: AsyncClient,
    get_session: Callable[[], AsyncContextManager[AsyncSession]],
    organization_id: str,
    inject_security_header: Callable[[str, str], None],
    clean_up_database: None,
):
    """Test if the finalize_aws_subscription endpoint returns a 409 status code when the subscription already exists."""  # noqa: E501
    async with get_session() as sess:
        query = insert(PendingAwsSubscriptionsModel).values(
            {
                "organization_id": organization_id,
                "product_code": product_code,
                "customer_identifier": customer_identifier,
                "customer_aws_account_id": customer_aws_account_id,
                "has_failed": False,
            }
        )
        await sess.execute(query)
        await sess.commit()

    inject_security_header("me", "admin:subscriptions:create")
    response = await test_client.post(
        "/admin/management/subscriptions/aws-subscription/finalize",
        json={
            "product_code": product_code,
            "customer_identifier": customer_identifier,
            "customer_aws_account_id": customer_aws_account_id,
        },
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {
        "message": "The organization already has a pending AWS subscription.",
        "error": None,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "product_code, customer_identifier, customer_aws_account_id, test_env, stage, app_domain",
    [
        ("XA13VSDU926V", "123", "123456789012", True, "production", "localhost"),
        ("BAKJH973MNDh", "321", "210987654321", True, "staging", "localhost"),
        (
            "eyothuq1lx973s1i7i7vpsbrp",
            "321",
            "210987654321",
            False,
            "production",
            "example.com",
        ),
        ("prbspv7i7i1s379xl1quhtoye", "321", "210987654321", False, "staging", "example.org"),
    ],
)
async def test_finalize_aws_subscription__check_http_201__new_subscription__check_free_trial_subscription(
    product_code: str,
    customer_identifier: str,
    customer_aws_account_id: str,
    test_env: bool,
    stage: str,
    app_domain: str,
    test_client: AsyncClient,
    get_session: Callable[[], AsyncContextManager[AsyncSession]],
    organization_id: str,
    inject_security_header: Callable[[str, str], None],
    clean_up_database: None,
):
    """Test if the finalize_aws_subscription endpoint creates a pending AWS subscription.

    This test ensures the correct behaviour when the customer has a free trial subscription.
    """
    query: Insert | Select
    async with get_session() as sess:
        query = select(SubscriptionTypeModel.id).where(
            SubscriptionTypeModel.name == SubscriptionTypesNames.cloud
        )
        cloud_type_id: int | None = (await sess.execute(query)).scalar_one_or_none()
        assert cloud_type_id is not None

        query = select(SubscriptionTierModel.id).where(
            SubscriptionTierModel.name == SubscriptionTiersNames.starter
        )
        starter_tier_id: int | None = (await sess.execute(query)).scalar_one_or_none()
        assert starter_tier_id is not None

        query = (
            insert(SubscriptionModel)
            .values(
                {
                    "organization_id": organization_id,
                    "type_id": cloud_type_id,
                    "tier_id": starter_tier_id,
                    "detail_data": {},
                    "created_at": datetime.now(tz=timezone.utc),
                    "expires_at": datetime.now(tz=timezone.utc) + timedelta(days=30),
                    "is_free_trial": True,
                }
            )
            .returning(SubscriptionModel.id)
        )
        free_trial_subscription_id: int = (await sess.execute(query)).scalar_one()
        await sess.commit()

    inject_security_header("me", "admin:subscriptions:create")
    with mock.patch("api.routers.subscriptions.SETTINGS.TEST_ENV", test_env), mock.patch(
        "api.routers.subscriptions.SETTINGS.STAGE", stage
    ), mock.patch("api.routers.subscriptions.SETTINGS.APP_DOMAIN", app_domain):
        response = await test_client.post(
            "/admin/management/subscriptions/aws-subscription/finalize",
            json={
                "product_code": product_code,
                "customer_identifier": customer_identifier,
                "customer_aws_account_id": customer_aws_account_id,
            },
        )

    async with get_session() as sess:
        query = select(SubscriptionModel).where(SubscriptionModel.id == free_trial_subscription_id)
        subscription: SubscriptionModel | None = (await sess.execute(query)).scalar_one_or_none()

        query = select(PendingAwsSubscriptionsModel).where(
            PendingAwsSubscriptionsModel.organization_id == organization_id
        )
        pending_subscription: PendingAwsSubscriptionsModel | None = (
            await sess.execute(query)
        ).scalar_one_or_none()

    response_data = PendingAwsSubscriptionModelOutput(**response.json())

    assert subscription is None
    assert pending_subscription is not None
    assert response.status_code == status.HTTP_201_CREATED
    assert response_data.id == pending_subscription.id
    assert response_data.organization_id == organization_id == pending_subscription.organization_id
    assert (
        response_data.customer_aws_account_id
        == customer_aws_account_id
        == pending_subscription.customer_aws_account_id
    )
    assert (
        response_data.customer_identifier == customer_identifier == pending_subscription.customer_identifier
    )
    assert response_data.product_code == product_code == pending_subscription.product_code
    assert response_data.has_failed is False
    assert pending_subscription.has_failed is False
    assert response.headers["set-cookie"] == (
        f'product_code=""; Domain={app_domain}; Max-Age=0; Path=/; SameSite=lax, '
        f'customer_identifier=""; Domain={app_domain}; Max-Age=0; Path=/; SameSite=lax, '
        f'customer_aws_account_id=""; Domain={app_domain}; Max-Age=0; Path=/; SameSite=lax'
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "product_code, customer_identifier, customer_aws_account_id, test_env, stage, app_domain",
    [
        ("XA13VSDU926V", "123", "123456789012", True, "production", "localhost"),
        ("BAKJH973MNDh", "321", "210987654321", True, "staging", "localhost"),
        (
            "eyothuq1lx973s1i7i7vpsbrp",
            "321",
            "210987654321",
            False,
            "production",
            "example.com",
        ),
        ("prbspv7i7i1s379xl1quhtoye", "321", "210987654321", False, "staging", "example.org"),
    ],
)
async def test_finalize_aws_subscription__check_http_201__new_subscription(
    product_code: str,
    customer_identifier: str,
    customer_aws_account_id: str,
    test_env: bool,
    stage: str,
    app_domain: str,
    test_client: AsyncClient,
    get_session: Callable[[], AsyncContextManager[AsyncSession]],
    organization_id: str,
    inject_security_header: Callable[[str, str], None],
    clean_up_database: None,
):
    """Test if the finalize_aws_subscription endpoint creates a pending AWS subscription.

    This test also ensures that the cookies product_code, customer_identifier, and customer_aws_account_id
    are set as expired after the endpoint is called. When the test environment is set to True, the endpoint
    must always set the cookie domain to localhost, otherwise, it should be the app domain.
    """
    inject_security_header("me", "admin:subscriptions:create")
    with mock.patch("api.routers.subscriptions.SETTINGS.TEST_ENV", test_env), mock.patch(
        "api.routers.subscriptions.SETTINGS.STAGE", stage
    ), mock.patch("api.routers.subscriptions.SETTINGS.APP_DOMAIN", app_domain):
        response = await test_client.post(
            "/admin/management/subscriptions/aws-subscription/finalize",
            json={
                "product_code": product_code,
                "customer_identifier": customer_identifier,
                "customer_aws_account_id": customer_aws_account_id,
            },
        )

    async with get_session() as sess:
        query = select(SubscriptionModel).where(SubscriptionModel.organization_id == organization_id)
        subscription: SubscriptionModel | None = (await sess.execute(query)).scalar_one_or_none()

        query = select(PendingAwsSubscriptionsModel).where(
            PendingAwsSubscriptionsModel.organization_id == organization_id
        )
        pending_subscription: PendingAwsSubscriptionsModel | None = (
            await sess.execute(query)
        ).scalar_one_or_none()

    response_data = PendingAwsSubscriptionModelOutput(**response.json())

    assert subscription is None
    assert pending_subscription is not None
    assert response.status_code == status.HTTP_201_CREATED
    assert response_data.id == pending_subscription.id
    assert response_data.organization_id == organization_id == pending_subscription.organization_id
    assert (
        response_data.customer_aws_account_id
        == customer_aws_account_id
        == pending_subscription.customer_aws_account_id
    )
    assert (
        response_data.customer_identifier == customer_identifier == pending_subscription.customer_identifier
    )
    assert response_data.product_code == product_code == pending_subscription.product_code
    assert response_data.has_failed is False
    assert pending_subscription.has_failed is False
    assert response.headers["set-cookie"] == (
        f'product_code=""; Domain={app_domain}; Max-Age=0; Path=/; SameSite=lax, '
        f'customer_identifier=""; Domain={app_domain}; Max-Age=0; Path=/; SameSite=lax, '
        f'customer_aws_account_id=""; Domain={app_domain}; Max-Age=0; Path=/; SameSite=lax'
    )


@pytest.mark.asyncio
@mock.patch("api.routers.subscriptions.unpack_organization_id_from_token")
async def test_get_pending_aws_subscription__check_http_error_400(
    mocked_unpack_organization_id_from_token: mock.MagicMock,
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test the get_pending_aws_subscription endpoint with a 400 error."""
    mocked_unpack_organization_id_from_token.side_effect = AssertionError("Organization not found in token")

    inject_security_header("me", "admin:subscriptions:read")
    response = await test_client.get("/admin/management/subscriptions/aws-subscription/pending")

    assert response.status_code == 400
    assert response.json() == {"message": "Organization not found in token", "error": None}


@pytest.mark.asyncio
async def test_get_pending_aws_subscription__check_http_error_404(
    inject_security_header: Callable,
    test_client: AsyncClient,
):
    """Test the get_pending_aws_subscription endpoint with a 404 error."""
    inject_security_header("me")
    response = await test_client.get("/admin/management/subscriptions/aws-subscription/pending")

    assert response.status_code == 404
    assert response.json() == {"message": "No pending AWS subscription found", "error": None}


@pytest.mark.asyncio
async def test_get_pending_aws_subscription__check_http_200(
    inject_security_header: Callable,
    test_client: AsyncClient,
    get_session: AsyncGenerator[AsyncSession, None],
    organization_id: str,
    clean_up_database: None,
):
    """Test the get_pending_aws_subscription endpoint with a 200 status code."""
    async with get_session() as sess:
        query = (
            insert(PendingAwsSubscriptionsModel)
            .values(
                organization_id=organization_id,
                product_code="XA13VSDU926V",
                customer_identifier="123",
                customer_aws_account_id="123456789012",
            )
            .returning(PendingAwsSubscriptionsModel.id)
        )
        pending_subscription_id: int = (await sess.execute(query)).scalar_one()

        await sess.commit()

    inject_security_header("me", "admin:subscriptions:read")
    response = await test_client.get("/admin/management/subscriptions/aws-subscription/pending")
    response_data = response.json()

    assert response.status_code == 200
    assert response_data["id"] == pending_subscription_id
    assert response_data["organization_id"] == organization_id
    assert response_data["product_code"] == "XA13VSDU926V"
    assert response_data["customer_identifier"] == "123"
    assert response_data["customer_aws_account_id"] == "123456789012"
    assert response_data["has_failed"] is False


@pytest.mark.asyncio
@mock.patch("api.routers.subscriptions.unpack_organization_id_from_token")
async def test_get_organization_free_trial__check_http_error_400(
    mocked_unpack_organization_id_from_token: mock.MagicMock,
    inject_security_header: Callable,
    test_client: AsyncClient,
    clean_up_database: None,
):
    """Test the get_organization_free_trial endpoint with a 400 error."""
    mocked_unpack_organization_id_from_token.side_effect = AssertionError("Organization not found in token")

    inject_security_header("me")
    response = await test_client.get("/admin/management/subscriptions/free-trial/check-availability")

    assert response.status_code == 400
    assert response.json() == {"message": "Organization not found in token", "error": None}


@pytest.mark.asyncio
async def test_get_organization_free_trial__check_http_200__not_available(
    inject_security_header: Callable,
    test_client: AsyncClient,
    get_session: AsyncGenerator[AsyncSession, None],
    organization_id: str,
    clean_up_database: None,
):
    """Test getting free trial when the free trial is not available."""
    async with get_session() as sess:
        query = insert(OrganizationFreeTrialsModel).values(organization_id=organization_id)
        await sess.execute(query)
        await sess.commit()

    inject_security_header("me")
    response = await test_client.get("/admin/management/subscriptions/free-trial/check-availability")

    assert response.status_code == 200
    assert response.json() == {"free_trial_available": False}


@pytest.mark.asyncio
async def test_get_organization_free_trial__check_http_200__available(
    inject_security_header: Callable,
    test_client: AsyncClient,
    clean_up_database: None,
):
    """Test getting free trial when the free trial is available."""
    inject_security_header("me")
    response = await test_client.get("/admin/management/subscriptions/free-trial/check-availability")

    assert response.status_code == 200
    assert response.json() == {"free_trial_available": True}


@pytest.mark.asyncio
@mock.patch("api.routers.subscriptions.unpack_organization_id_from_token")
async def test_create_organization_free_trial__check_http_error_400(
    mocked_unpack_organization_id_from_token: mock.MagicMock,
    inject_security_header: Callable,
    test_client: AsyncClient,
    clean_up_database: None,
):
    """Test the create_organization_free_trial endpoint with a 400 error."""
    mocked_unpack_organization_id_from_token.side_effect = AssertionError("Organization not found in token")

    inject_security_header("me")
    response = await test_client.post("/admin/management/subscriptions/free-trial")

    assert response.status_code == 400
    assert response.json() == {"message": "Organization not found in token", "error": None}


@pytest.mark.asyncio
async def test_create_organization_free_trial__check_http_409(
    inject_security_header: Callable,
    test_client: AsyncClient,
    get_session: AsyncGenerator[AsyncSession, None],
    organization_id: str,
    clean_up_database: None,
):
    """Test if the free trial creation endpoint returns a 409 status code when free trial already exists."""
    async with get_session() as sess:
        query = insert(OrganizationFreeTrialsModel).values(organization_id=organization_id)
        await sess.execute(query)
        await sess.commit()

    inject_security_header("me")
    response = await test_client.post("/admin/management/subscriptions/free-trial")

    assert response.status_code == 409
    assert response.json() == {"message": "Organization already has a free trial", "error": None}


@pytest.mark.asyncio
async def test_create_organization_free_trial__check_http_201(
    inject_security_header: Callable,
    test_client: AsyncClient,
    get_session: AsyncGenerator[AsyncSession, None],
    organization_id: str,
    clean_up_database: None,
):
    """Test if the free trial creation endpoint returns a 201 status code when free trial is created."""
    inject_security_header("me")
    response = await test_client.post("/admin/management/subscriptions/free-trial")
    response_data = SubscriptionModelOutput(**response.json())

    async with get_session() as sess:
        query = select(OrganizationFreeTrialsModel).where(
            OrganizationFreeTrialsModel.organization_id == organization_id
        )
        free_trial: OrganizationFreeTrialsModel | None = (await sess.execute(query)).scalar_one_or_none()

        query = select(SubscriptionModel).where(SubscriptionModel.organization_id == organization_id)
        free_trial_subscription: SubscriptionModel | None = (await sess.execute(query)).scalar_one_or_none()
        assert free_trial_subscription is not None

        query = select(SubscriptionTypeModel.id).where(
            SubscriptionTypeModel.name == SubscriptionTypesNames.cloud
        )
        type_id: int = (await sess.execute(query)).scalar_one()

        query = select(SubscriptionTierModel.id).where(
            SubscriptionTierModel.name == SubscriptionTiersNames.starter
        )
        tier_id: int = (await sess.execute(query)).scalar_one()

    assert response.status_code == 201
    assert free_trial is not None
    assert free_trial_subscription is not None
    assert response_data.id == free_trial_subscription.id
    assert organization_id == free_trial.organization_id == free_trial_subscription.organization_id
    assert response_data.is_free_trial is True
    assert free_trial_subscription.is_free_trial is True
    assert response_data.type_id == free_trial_subscription.type_id == type_id
    assert response_data.tier_id == free_trial_subscription.tier_id == tier_id
