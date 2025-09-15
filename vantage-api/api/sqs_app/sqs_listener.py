"""SQS Listener module for handling AWS Marketplace related operations.

This module provides functions to listen to specific AWS SQS topics related
to marketplace notifications and subscriptions. It processes messages received
from these topics asynchronously and interacts with a PostgreSQL database
to handle marketplace-related operations.
"""

import asyncio
import json
import threading
import time
from typing import Dict

import boto3
from sqlalchemy import delete, insert, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.mktplace_entitlement_app.mktplace_entitlement_ops import (
    assume_entitlement_role,
)
from api.routers.subscriptions import helpers
from api.settings import SETTINGS
from api.sql_app import models as db_models
from api.sql_app.enums import SubscriptionTiersNames, SubscriptionTypesNames
from api.sql_app.schemas import SubscriptionRow
from api.sql_app.session import create_async_session
from api.utils.logging import logger


async def get_dbs():
    """Return a list of all organization databases."""
    session = await create_async_session("postgres", False)
    async with session() as sess:
        db_list = await sess.execute(
            text(
                "SELECT datname FROM pg_database WHERE datname ~ '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$';"  # noqa
            )
        )
        await sess.close()

    return db_list.scalars().all()


async def subscribe_success(parsed_sns_message: Dict[str, str], sess: AsyncSession):
    """Subscribe a customer to a service upon successful subscription.

    Args:
    ----
        parsed_sns_message (Dict[str, str]): A dictionary containing parsed SNS message
            with keys:
            - "action": The action name.
            - "customer-identifier": Identifier for the customer.
            - "product-code": The product code.
            - "offer-identifier": Identifier for the offer.
            - "isFreeTrialTermPresent": String representation indicating if a free trial term is present.

        sess (AsyncSession): An asynchronous SQLAlchemy session.

    """
    logger.debug("Processing subscribe success")
    customer_identifier = parsed_sns_message["customer-identifier"]

    query = select(db_models.PendingAwsSubscriptionsModel).where(
        db_models.PendingAwsSubscriptionsModel.customer_identifier == customer_identifier
    )
    pending_subscription: db_models.PendingAwsSubscriptionsModel = (
        await sess.execute(query)
    ).scalar_one_or_none()

    if pending_subscription is None:
        logger.debug(f"Empty pending subscription for the customer: {customer_identifier}")
        return False

    # Check if the subscription already exists
    query = select(db_models.SubscriptionModel).where(
        db_models.SubscriptionModel.organization_id == pending_subscription.organization_id
    )
    existent_subscription: db_models.SubscriptionModel = (await sess.execute(query)).scalar_one_or_none()

    is_free_trial = parsed_sns_message.get("isFreeTrialTermPresent", "false") == "true"
    if existent_subscription is not None:
        existent_subscription = SubscriptionRow.from_orm(existent_subscription)
        existent_subscription.detail_data.update(unsubscribe_pending=False)

        query = (
            update(db_models.SubscriptionModel)
            .where(db_models.SubscriptionModel.id == existent_subscription.id)
            .values(
                {
                    "detail_data": existent_subscription.detail_data,
                    "is_free_trial": is_free_trial,
                }
            )
            .returning(db_models.SubscriptionModel)
        )

    else:
        tier_id = await helpers.get_tier_id_by_name(sess, SubscriptionTiersNames.starter)
        type_id = await helpers.get_type_id_by_name(sess, SubscriptionTypesNames.aws)
        subscription_data = {
            "organization_id": pending_subscription.organization_id,
            "type_id": type_id,
            "tier_id": tier_id,
            "detail_data": {
                "customer_identifier": pending_subscription.customer_identifier,
                "customer_aws_account_id": pending_subscription.customer_aws_account_id,
                "product_code": pending_subscription.product_code,
                "unsubscribe_pending": False,
            },
            "expires_at": None,
            "is_free_trial": is_free_trial,
        }

        query = (
            insert(db_models.SubscriptionModel)
            .values(subscription_data)
            .returning(db_models.SubscriptionModel)
        )

    subscription_result: db_models.SubscriptionModel = (await sess.execute(query)).one_or_none()

    if subscription_result is not None:
        logger.debug(f"New Subscription result: {subscription_result}")
        subscription = SubscriptionRow.from_orm(subscription_result)

        query = select(db_models.OrganizationFreeTrialsModel).where(
            db_models.OrganizationFreeTrialsModel.organization_id == pending_subscription.organization_id
        )
        organization_free_trial = (await sess.execute(query)).scalar_one_or_none()

        if is_free_trial and organization_free_trial is None:
            query = insert(db_models.OrganizationFreeTrialsModel).values(
                {"organization_id": pending_subscription.organization_id}
            )
            result = (await sess.execute(query)).scalar_one_or_none()
            logger.debug(f"Free trial created: {result}")

        query = delete(db_models.PendingAwsSubscriptionsModel).where(
            db_models.PendingAwsSubscriptionsModel.id == pending_subscription.id
        )
        await sess.execute(query)

        logger.debug(
            f"""
                Subscription with Id={subscription.id} and
                orgId={subscription.organization_id}
                was created with free_trial={is_free_trial}
            """
        )
        await sess.commit()
        return True
    else:
        await sess.rollback()
        logger.debug(f"Subscription couldn't be created: {result}")
        return False


async def subscribe_fail(customer_identifier: str, sess: AsyncSession):
    """Mark a pending subscription attempt as failed for a customer.

    Args:
    ----
        customer_identifier (str): Identifier for the customer whose subscription failed.
        sess (AsyncSession): An asynchronous SQLAlchemy session.

    """
    query = (
        update(db_models.PendingAwsSubscriptionsModel)
        .where(db_models.PendingAwsSubscriptionsModel.customer_identifier == customer_identifier)
        .values(has_failed=True)
        .returning(db_models.PendingAwsSubscriptionsModel)
    )
    result: db_models.PendingAwsSubscriptionsModel = (await sess.execute(query)).one_or_none()

    if result is not None:
        await sess.commit()
        logger.debug(
            f"""
                Pending Subscription with Id={result.id} and
                orgId={result.organization_id} failed
            """
        )
        return True
    else:
        logger.debug(
            f"""
                Error while updating pending subscription for failed subscription
                Customer Identifier: {customer_identifier}
                DB info: {sess.info}
            """
        )
        return False


async def unsubscribe_success(customer_identifier: str, sess: AsyncSession):
    """Unsubscribe a customer from a service upon successful subscription.

    Args:
    ----
        customer_identifier (str): Identifier for the customer to be unsubscribed.
        sess (AsyncSession): An asynchronous SQLAlchemy session.

    """
    logger.debug(f"Unsubscribing customer: {customer_identifier}, Db Info: {sess.info}")
    query = select(db_models.SubscriptionModel).where(
        db_models.SubscriptionModel.detail_data["customer_identifier"].astext == customer_identifier
    )
    subscription: db_models.SubscriptionModel | None = (await sess.execute(query)).scalar_one_or_none()
    logger.debug(f"Existent subscription to delete {subscription}")
    if subscription is not None:
        query = (
            delete(db_models.SubscriptionModel)
            .where(db_models.SubscriptionModel.id == subscription.id)
            .returning(db_models.SubscriptionModel)
        )
        result: db_models.SubscriptionModel = (await sess.execute(query)).one_or_none()
        await sess.commit()

        if result is not None:
            logger.debug(
                f"""
                    Subscription with Id={result.id} and
                    orgId={result.organization_id}
                    was deleted
                """
            )
            return True
        else:
            logger.debug("No subscriptions found")
            return False


async def unsubscribe_pending(customer_identifier: str, sess: AsyncSession):
    """Update the unsubscribe_pending flag in a subscription.

    Args:
    ----
        customer_identifier (str): Identifier for the customer to be updated.
        sess (AsyncSession): An asynchronous SQLAlchemy session.

    """
    logger.debug(f"Updating unsubscribing for customer: {customer_identifier}.")

    query = select(db_models.SubscriptionModel).where(
        db_models.SubscriptionModel.detail_data["customer_identifier"].astext == customer_identifier
    )

    subscription: db_models.SubscriptionModel | None = (await sess.execute(query)).scalar_one_or_none()

    if subscription is None:
        logger.debug(
            f"""
                No subscription found
                for customer: {customer_identifier}
            """
        )
        return False

    subscription = SubscriptionRow.from_orm(subscription)
    subscription.detail_data.update(unsubscribe_pending=True)
    query = (
        update(db_models.SubscriptionModel)
        .where(db_models.SubscriptionModel.id == subscription.id)
        .values(
            {
                "detail_data": subscription.detail_data,
            }
        )
        .returning(db_models.SubscriptionModel)
    )

    result = (await sess.execute(query)).one_or_none()
    await sess.commit()

    if result is None:
        logger.debug(
            f"""
                Fail to update unsubscribing pending
                for customer: {customer_identifier}
                and org: {subscription.organization_id}
            """
        )
        return False

    logger.debug(
        f"""
            Unsubscribe pending updated
            for customer: {customer_identifier}
            and org: {subscription.organization_id}
        """
    )
    return True


async def process_subscription(message: str):
    """Process the messages coming from marketplace subscription topic."""
    try:
        parsed_message = json.loads(message)
        parsed_sns_message = json.loads(parsed_message["Message"])
        logger.debug(f"Message: {parsed_sns_message}")

        logger.debug(f"Received message: {parsed_sns_message}")

        # TODO - This method can be inefficient with many dbs. Ideally, it should be change in the future to use postgres_fdw # noqa
        db_list = await get_dbs()
        result = False
        for db in db_list:
            session = await create_async_session(db, False)
            async with session() as sess:
                if parsed_sns_message["action"] == "subscribe-success":
                    result = await subscribe_success(parsed_sns_message=parsed_sns_message, sess=sess)
                elif parsed_sns_message["action"] == "subscribe-fail":
                    result = await subscribe_fail(
                        customer_identifier=parsed_sns_message["customer-identifier"], sess=sess
                    )
                elif parsed_sns_message["action"] == "unsubscribe-pending":
                    result = await unsubscribe_pending(
                        customer_identifier=parsed_sns_message["customer-identifier"], sess=sess
                    )
                elif parsed_sns_message["action"] == "unsubscribe-success":
                    result = await unsubscribe_success(
                        customer_identifier=parsed_sns_message["customer-identifier"], sess=sess
                    )
            if result:
                break

        return result
    except Exception as e:
        logger.debug(f"Process subscription function ended with error: {e}")
        return False


async def get_sqs(topic: str, handle_message):
    """Get the messages from a given SQS topic.

    The function will call the handle_message function to each message.
    """
    try:
        sqs_client = boto3.client("sqs", **assume_entitlement_role())
        response = sqs_client.receive_message(
            QueueUrl=topic, MaxNumberOfMessages=SETTINGS.SQS_MAX_NUMBER_OF_MESSAGES, WaitTimeSeconds=20
        )
        logger.debug(f"SQS Topic response: {response}")
        if "Messages" in response:
            logger.info("Processing messages from notification topic")
            for message in response["Messages"]:
                success = await handle_message(message["Body"])
                # Delete the message from the queue if the message was processed with success
                if success:
                    logger.debug(f"Deleting message from topic: {message}")
                    sqs_client.delete_message(QueueUrl=topic, ReceiptHandle=message["ReceiptHandle"])
        else:
            logger.debug("No messages received from notification topic")
    except Exception as e:
        logger.debug(f"Error: {e}")


async def _loop_function(sqs_function_params):
    """Listen the topics each 5 seconds."""
    logger.debug("SQS Listener started")
    while True:
        await get_sqs(**sqs_function_params)
        time.sleep(5)  # Wait 5 seconds before retrying


def _init_sqs_thread(sqs_function_params):
    """Start an asyncio function in the thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_loop_function(sqs_function_params))


def init_sqs_listeners():
    """Create and start the listeners threads for each topic."""
    try:
        subscriptions_thread = threading.Thread(
            target=_init_sqs_thread,
            args=(
                {
                    "topic": SETTINGS.AWS_MKT_SUBSCRIPTION_TOPIC,
                    "handle_message": process_subscription,
                },
            ),
        )
        subscriptions_thread.start()
    except Exception as e:
        logger.debug(f"Something when wrong when try to start the SQS listener: {e}")
