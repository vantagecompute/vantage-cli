"""Core module for testing the SQS listener."""
import json
from collections.abc import Callable
from datetime import datetime
from typing import AsyncContextManager
from unittest import mock

import pytest
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Insert, Select

from api.settings import SETTINGS
from api.sql_app import models
from api.sql_app.enums import SubscriptionTiersNames, SubscriptionTypesNames
from api.sqs_app.sqs_listener import (
    get_sqs,
    process_subscription,
    subscribe_fail,
    subscribe_success,
    unsubscribe_pending,
    unsubscribe_success,
)


@pytest.mark.asyncio
@mock.patch("api.sqs_app.sqs_listener.boto3.client")
@mock.patch("api.sqs_app.sqs_listener.assume_entitlement_role")
async def test_sqs_listener_when_there_is_message_in_queue(
    assume_entitlement_role_mock: mock.Mock,
    boto3_client_mock: mock.Mock,
):
    """Test the get_sqs function to check if it is able to retrieve the available messages in the queue."""
    topic = "dummy_topic"

    handle_message = mock.AsyncMock()

    response = {
        "Messages": [
            {
                "MessageId": "f40b7082-3bd8-44d0-b0f7-fa0bfca1c71d",
                "ReceiptHandle": "AQEB8KDmkBfJj63VUXnR6o0CgSPIj8s2Lb+cie3ttXzuMlvC8KLHYKWMbjKlLkl8bw4wxniE15zdOb0fuvsAtqNIs/Z7ZX7ZZw1sWSn4P2BjixYX8vrHGco1ZG17dLK4Di/hyDBEjNUksw/bVeHxFILwyMpYUYumO9vQ9fu57Kft6N7jBVOP4k6c7zQQjFUIRy2sarEjZWUJImfnhzHmWKe/PKZdmi9XwukSIGxmA6bQOcjYmkPvq4JjUmhlFuMVKxnvXZhVH1zeX+sty4sweDhmlhyMR82X1kIdhQijNZvqQOo0hAISW1tGIHwBwfayqZiifvG8zNM23r2pLVxzSu4FDlYIUMpvdo5jZJgU8UCI+oDI62S3TPbZE8XamiIiJRZ5vVt3XGZeIFS+8MvelUIafQ==",  # noqa
                "MD5OfBody": "fa0df0bd95e9502055a67cf310e8ac4f",
                "Body": '{\n  "Type" : "Notification",\n  "MessageId" : "a8f61e4d-f4b7-579b-87e7-40207272cedc",\n  "TopicArn" : "arn:aws:sns:us-east-1:287250355862:aws-mp-entitlement-notification-eyothuq1lx973s1i7i7vpsbrp",\n  "Message" : "{\\n\\"action\\": \\"entitlement-updated\\",\\n\\"customer-identifier\\": \\"Xic6cTJByKE\\",\\n\\"product-code\\": \\"eyothuq1lx973s1i7i7vpsbrp\\"\\n}",\n  "Timestamp" : "2024-03-14T23:13:09.416Z",\n  "SignatureVersion" : "1",\n  "Signature" : "bI44w9SFSKrZCYeKzjP7LBgdWkCer/I5uokJW4bgA14r2YA1M+WYSH1JaFz9RoORbC4mEkFjuY9uoFERqvFnWP1B9Z83mKAMdETbaPQn7zfADkz+ARcagSbXWGCvbgH+G/NszrWdQLVekhaNf9H3dOEUnL6OERF9FZjWg7qxJCfjpqcuoV2+KSq2eLrptb1RHscyGcvOVpucBWwV6/hbRzdPiaoo0odrGNKDXHpB0Y4jX3wF5/8qUCTmTYrgEYwJcc+FnCotcl+ujoBJ5T2X6fjLPpoYcaBXmTxNxzMuBKndcN4pQCuQQEcaBPHJwlwDQmog78Zl0WD12fTuRV9TdA==",\n  "SigningCertURL" : "https://sns.us-east-1.amazonaws.com/SimpleNotificationService-60eadc530605d63b8e62a523676ef735.pem",\n  "UnsubscribeURL" : "https://sns.us-east-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-east-1:287250355862:aws-mp-entitlement-notification-eyothuq1lx973s1i7i7vpsbrp:649d64c4-7d7d-46df-bbf5-2c471ab8b38f"\n}',  # noqa
            }
        ]
    }

    sqs_client_mock = mock.Mock()
    sqs_client_mock.receive_message = mock.Mock(return_value=response)
    sqs_client_mock.delete_message = mock.Mock()

    assume_entitlement_role_mock.return_value = {}
    boto3_client_mock.return_value = sqs_client_mock

    await get_sqs(topic=topic, handle_message=handle_message)

    handle_message.assert_called_with(response["Messages"][0]["Body"])
    assume_entitlement_role_mock.assert_called_once_with()
    boto3_client_mock.assert_called_once_with(
        "sqs",
        **assume_entitlement_role_mock.return_value,
    )
    sqs_client_mock.receive_message.assert_called_once_with(
        QueueUrl=topic, MaxNumberOfMessages=SETTINGS.SQS_MAX_NUMBER_OF_MESSAGES, WaitTimeSeconds=20
    )
    sqs_client_mock.delete_message.assert_called_once_with(
        QueueUrl=topic, ReceiptHandle=response["Messages"][0]["ReceiptHandle"]
    )


@pytest.mark.asyncio
@mock.patch("api.sqs_app.sqs_listener.boto3.client")
@mock.patch("api.sqs_app.sqs_listener.assume_entitlement_role")
async def test_sqs_listener_catch_errors_from_handle_functions(
    assume_entitlement_role_mock: mock.Mock,
    boto3_client_mock: mock.Mock,
):
    """Test the get_sqs function to check if it handles exceptions."""
    topic = "dummy_topic"

    handle_message = mock.AsyncMock(side_effect=Exception("Error"))

    response = {"Messages": [{"Body": '{"value": "stringified json"}', "ReceiptHandle": "receipt"}]}
    sqs_client_mock = mock.Mock()
    sqs_client_mock.receive_message = mock.Mock(return_value=response)
    sqs_client_mock.delete_message = mock.Mock()

    assume_entitlement_role_mock.return_value = {}
    boto3_client_mock.return_value = sqs_client_mock

    await get_sqs(topic=topic, handle_message=handle_message)

    handle_message.assert_called_with(response["Messages"][0]["Body"])
    assume_entitlement_role_mock.assert_called_once_with()
    boto3_client_mock.assert_called_once_with(
        "sqs",
        **assume_entitlement_role_mock.return_value,
    )
    sqs_client_mock.receive_message.assert_called_once_with(
        QueueUrl=topic, MaxNumberOfMessages=SETTINGS.SQS_MAX_NUMBER_OF_MESSAGES, WaitTimeSeconds=20
    )
    sqs_client_mock.delete_message.assert_not_called()


@pytest.mark.asyncio
@mock.patch("api.sqs_app.sqs_listener.boto3.client")
@mock.patch("api.sqs_app.sqs_listener.assume_entitlement_role")
async def test_sqs_listener_when_there_is_no_message_in_queue(
    assume_entitlement_role_mock: mock.Mock,
    boto3_client_mock: mock.Mock,
):
    """Test the get_sqs function to check the behaviour when there's no message in the queue."""
    topic = "dummy_topic"

    sqs_client_mock = mock.Mock()
    handle_message = mock.AsyncMock()
    sqs_client_mock.receive_message = mock.Mock(return_value={})
    sqs_client_mock.delete_message = mock.Mock()

    assume_entitlement_role_mock.return_value = {}
    boto3_client_mock.return_value = sqs_client_mock

    await get_sqs(topic=topic, handle_message=handle_message)

    handle_message.assert_not_called()
    assume_entitlement_role_mock.assert_called_once_with()
    boto3_client_mock.assert_called_once_with(
        "sqs",
        **assume_entitlement_role_mock.return_value,
    )
    sqs_client_mock.receive_message.assert_called_once_with(
        QueueUrl=topic, MaxNumberOfMessages=SETTINGS.SQS_MAX_NUMBER_OF_MESSAGES, WaitTimeSeconds=20
    )
    sqs_client_mock.delete_message.assert_not_called()


@pytest.mark.asyncio
@mock.patch("api.sqs_app.sqs_listener.subscribe_success")
@mock.patch("api.sqs_app.sqs_listener.subscribe_fail")
@mock.patch("api.sqs_app.sqs_listener.unsubscribe_success")
@pytest.mark.parametrize(
    "action_name",
    ["subscribe-success", "subscribe-fail", "unsubscribe-success"],
)
async def test_sqs_listener_process_subscription_with_success(
    mocked_unsubscribe_success: mock.AsyncMock,
    mocked_subscribe_fail: mock.AsyncMock,
    mocked_subscribe_success: mock.AsyncMock,
    action_name: str,
    clean_up_database: None,
):
    """Test the process_subscription function to check if it will call the correct function."""
    message = json.dumps(
        {
            "Type": "Subscription",
            "MessageId": "a8f61e4d-f4b7-579b-87e7-40207272cedc",
            "TopicArn": SETTINGS.AWS_MKT_SUBSCRIPTION_TOPIC,
            "Message": json.dumps(
                {
                    "action": action_name,
                    "customer-identifier": "X01EXAMPLEX",
                    "product-code": "n0123EXAMPLEXXXXXXXXXXXX",
                    "offer-identifier": "offer-abcexample123",
                    "isFreeTrialTermPresent": "true",
                }
            ),
            "Timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
            "SignatureVersion": "1",
            "Signature": "123123/1asdasd",
            "SigningCertURL": "http://dummy",
            "UnsubscribeURL": "http://dummy",
        }
    )

    patches = {
        "subscribe-success": lambda: mocked_subscribe_success,
        "subscribe-fail": lambda: mocked_subscribe_fail,
        "unsubscribe-success": lambda: mocked_unsubscribe_success,
    }

    with mock.patch("api.sqs_app.sqs_listener.SETTINGS.TEST_ENV", True):
        await process_subscription(message)

    for action in list(patches.keys()):
        if action == action_name:
            patches[action]().assert_called_once()
        else:
            patches[action]().assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "product_code, customer_identifier, customer_aws_account_id",
    [
        ("XA13VSDU926V", "123", "123456789012"),
    ],
)
async def test_sqs_listener_unsubscribe_success(
    product_code: str,
    customer_identifier: str,
    customer_aws_account_id: str,
    get_session: Callable[[], AsyncContextManager[AsyncSession]],
    organization_id: str,
    clean_up_database: None,
):
    """Test the unsubscribe_success function to check if it will delete the record in the DB."""
    subscription_tier_name = SubscriptionTiersNames("starter")
    subscription_type_name = SubscriptionTypesNames("aws")

    async with get_session() as sess:
        query: Select | Insert
        query = select(models.SubscriptionTierModel.id).where(
            models.SubscriptionTierModel.name == subscription_tier_name.value
        )
        tier_id = (await sess.execute(query)).scalars().first()

        query = select(models.SubscriptionTypeModel.id).where(
            models.SubscriptionTypeModel.name == subscription_type_name.value
        )
        type_id = (await sess.execute(query)).scalars().first()

        query = (
            insert(models.SubscriptionModel)
            .values(
                organization_id=organization_id,
                type_id=type_id,
                tier_id=tier_id,
                detail_data={
                    "product_code": product_code,
                    "customer_identifier": customer_identifier,
                    "customer_aws_account_id": customer_aws_account_id,
                },
                expires_at=None,
                is_free_trial=False,
            )
            .returning(models.SubscriptionModel)
        )
        subscription_id: int
        subscription_id = (await sess.execute(query)).fetchone().id
        await sess.commit()

    with mock.patch("api.sqs_app.sqs_listener.SETTINGS.TEST_ENV", True):
        async with get_session() as sess:
            await unsubscribe_success(customer_identifier, sess)
            await sess.close()

    async with get_session() as sess:
        query = select(models.SubscriptionModel).where(models.SubscriptionModel.id == subscription_id)

        result = (await sess.execute(query)).scalar_one_or_none()
        await sess.close()

    assert result is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "product_code, customer_identifier, customer_aws_account_id",
    [
        ("XA13VSDU926V", "123", "123456789012"),
    ],
)
async def test_sqs_listener_subscribe_fail(
    product_code: str,
    customer_identifier: str,
    customer_aws_account_id: str,
    get_session: Callable[[], AsyncContextManager[AsyncSession]],
    organization_id: str,
    clean_up_database: None,
):
    """Test the subscribe_fail function to check if it will update the pending subscription."""
    async with get_session() as sess:
        query = (
            insert(models.PendingAwsSubscriptionsModel)
            .values(
                organization_id=organization_id,
                customer_aws_account_id=customer_aws_account_id,
                customer_identifier=customer_identifier,
                product_code=product_code,
                has_failed=False,
            )
            .returning(models.PendingAwsSubscriptionsModel.id)
        )
        pending_subscription_id: int
        pending_subscription_id = (await sess.execute(query)).fetchone().id
        await sess.commit()

    with mock.patch("api.sqs_app.sqs_listener.SETTINGS.TEST_ENV", True):
        async with get_session() as sess:
            await subscribe_fail(customer_identifier, sess)
            await sess.close()

    async with get_session() as sess:
        query = select(models.PendingAwsSubscriptionsModel).where(
            models.PendingAwsSubscriptionsModel.id == pending_subscription_id
        )

        result = (await sess.execute(query)).scalar_one_or_none()
        await sess.close()

    assert result.has_failed is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "product_code, customer_identifier, customer_aws_account_id",
    [
        ("XA13VSDU926V", "123", "123456789012"),
    ],
)
async def test_sqs_listener_subscribe_success__test_when_the_function_return_with_success(
    product_code: str,
    customer_identifier: str,
    customer_aws_account_id: str,
    get_session: Callable[[], AsyncContextManager[AsyncSession]],
    organization_id: str,
    clean_up_database: None,
):
    """Test the subscribe_success function to check if it will create the records in the DB."""
    message = {
        "action": "subscribe-sucess",
        "customer-identifier": customer_identifier,
        "product-code": product_code,
        "offer-identifier": "offer-abcexample123",
        "isFreeTrialTermPresent": "true",
    }

    async with get_session() as sess:
        query = (
            insert(models.PendingAwsSubscriptionsModel)
            .values(
                organization_id=organization_id,
                customer_aws_account_id=customer_aws_account_id,
                customer_identifier=customer_identifier,
                product_code=product_code,
                has_failed=False,
            )
            .returning(models.PendingAwsSubscriptionsModel.id)
        )
        await sess.execute(query)
        await sess.commit()

    with mock.patch("api.sqs_app.sqs_listener.SETTINGS.TEST_ENV", True):
        async with get_session() as sess:
            await subscribe_success(parsed_sns_message=message, sess=sess)
            await sess.close()

    async with get_session() as sess:
        query = select(models.SubscriptionTierModel.id).where(
            models.SubscriptionTierModel.name == SubscriptionTiersNames("starter").value
        )
        tier_id = (await sess.execute(query)).scalars().first()

        query = select(models.SubscriptionTypeModel.id).where(
            models.SubscriptionTypeModel.name == SubscriptionTypesNames("aws").value
        )
        type_id = (await sess.execute(query)).scalars().first()

        query = select(models.SubscriptionModel).where(
            models.SubscriptionModel.detail_data["customer_identifier"].astext == customer_identifier
        )

        result: models.SubscriptionModel = (await sess.execute(query)).scalar_one_or_none()

        query = select(models.OrganizationFreeTrialsModel).where(
            models.OrganizationFreeTrialsModel.organization_id == organization_id
        )
        free_trial_result = (await sess.execute(query)).scalar_one_or_none()

        await sess.close()

    assert result is not None
    assert free_trial_result is not None
    assert free_trial_result.organization_id == organization_id
    assert result.is_free_trial is True
    assert result.type_id == type_id
    assert result.tier_id == tier_id
    assert result.detail_data == {
        "customer_identifier": customer_identifier,
        "customer_aws_account_id": customer_aws_account_id,
        "product_code": product_code,
        "unsubscribe_pending": False,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "product_code, customer_identifier, customer_aws_account_id",
    [
        ("XA13VSDU926V", "123", "123456789012"),
    ],
)
async def test_sqs_listener_unsubscribe_pending__test_when_the_function_return_with_success(
    product_code: str,
    customer_identifier: str,
    customer_aws_account_id: str,
    get_session: Callable[[], AsyncContextManager[AsyncSession]],
    organization_id: str,
    clean_up_database: None,
):
    """Test the unsubscribe_pending function to check if it will update the records in the DB."""
    subscription_data = {
        "organization_id": organization_id,
        "type_id": 1,
        "tier_id": 1,
        "detail_data": {
            "customer_identifier": customer_identifier,
            "customer_aws_account_id": customer_aws_account_id,
            "product_code": product_code,
            "unsubscribe_pending": False,
        },
        "expires_at": None,
        "is_free_trial": True,
    }

    async with get_session() as sess:
        query = (
            insert(models.SubscriptionModel).values(subscription_data).returning(models.SubscriptionModel.id)
        )
        await sess.execute(query)
        await sess.commit()

    with mock.patch("api.sqs_app.sqs_listener.SETTINGS.TEST_ENV", True):
        async with get_session() as sess:
            await unsubscribe_pending(customer_identifier, sess)
            await sess.close()

    async with get_session() as sess:
        query = select(models.SubscriptionModel).where(
            models.SubscriptionModel.detail_data["customer_identifier"].astext == customer_identifier
        )

        result: models.SubscriptionModel = (await sess.execute(query)).scalar_one_or_none()
        await sess.close()

    assert result is not None
    assert result.detail_data == {
        "customer_identifier": customer_identifier,
        "customer_aws_account_id": customer_aws_account_id,
        "product_code": product_code,
        "unsubscribe_pending": True,
    }
