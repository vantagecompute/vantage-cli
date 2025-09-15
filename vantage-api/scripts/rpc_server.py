"""RPC server to handle requests from the broker."""
import asyncio
import json
import os
from typing import Callable

import aiormq
from aio_pika import Message, connect
from aio_pika.abc import AbstractIncomingMessage
from loguru import logger
from pamqp.commands import Basic

from api.broker_app.helpers import OrganizationActionPayload
from scripts import create_resources, delete_resources


async def main() -> None:
    """Orchestrate the RPC server logic."""
    # Perform connection
    connection = await connect(
        "amqp://{}:{}@{}/{}".format(
            os.environ.get("RABBITMQ_USER", "guest"),
            os.environ.get("RABBITMQ_PASS", "guest"),
            os.environ.get("RABBITMQ_HOST", "localhost"),
            os.environ.get("RABBITMQ_VHOST", "internal"),
        )
    )

    # Create a channel
    channel = await connection.channel()

    # Fetch queue
    queue = await channel.get_queue(os.environ.get("RABBITMQ_QUEUE", "notifications-api"), ensure=True)
    service_name = queue.name.replace("-", "_")

    logger.info(" [x] Awaiting RPC requests")

    # Start listening the queue whose name is defined as an environment variable
    async with queue.iterator() as qiterator:
        message: AbstractIncomingMessage
        async for message in qiterator:
            try:
                async with message.process(requeue=False):
                    assert message.reply_to is not None
                    logger.debug(
                        (
                            "Received message: "
                            f"correlation_id={message.correlation_id} reply_to={message.reply_to}"
                        )
                    )

                    # check out api/broker_app/helpers.py for details about the payload data
                    message_payload: OrganizationActionPayload = json.loads(message.body.decode())

                    tenant = message_payload.get("tenant")
                    action = message_payload.get("action")
                    assert tenant is not None  # mypy assertion
                    assert action is not None  # mypy assertion
                    logger.info(f"Processing request {action} for tenant {tenant}")

                    match action:
                        case "create_organization":
                            helper_function: Callable[[str], None] = getattr(create_resources, service_name)
                            response = "True".encode()
                        case "delete_organization":
                            helper_function: Callable[[str], None] = getattr(delete_resources, service_name)
                            response = "True".encode()
                        case _:
                            logger.error(f"Unknown action {action}")

                            def helper_function(tenant):
                                return None

                            response = "False".encode()

                    # Execute the helper function
                    assert helper_function is not None  # mypy assertion
                    helper_function(tenant)

                    try:
                        confirmation: aiormq.abc.ConfirmationFrameType | None = (
                            await channel.default_exchange.publish(
                                Message(
                                    body=response,
                                    correlation_id=message.correlation_id,
                                ),
                                routing_key=message.reply_to,
                            )
                        )
                    except Exception as err:
                        logger.exception(f"Error while publishing RPC response: {err}")
                    else:
                        if not isinstance(confirmation, Basic.Ack):
                            logger.error(f"Confirmation of {message} failed: {confirmation}")
                            raise RuntimeError
                        logger.info("Request complete")
            except Exception:
                logger.exception("Processing error for message %r", message)


if __name__ == "__main__":
    asyncio.run(main())
