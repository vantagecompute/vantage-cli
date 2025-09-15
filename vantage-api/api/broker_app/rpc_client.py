"""Core module for messaging related operations."""
from __future__ import annotations

# fmt: off
import nest_asyncio

nest_asyncio.apply()
# fmt: on

import asyncio
import socket
import uuid
from typing import MutableMapping, Union

import aio_pika
import aiormq
from aiormq.exceptions import DeliveryError
from loguru import logger
from pamqp.commands import Basic

from api.settings import SETTINGS


class RabbitMQRpcClient:

    """RabbitMQ RPC client."""

    connection: aio_pika.abc.AbstractConnection
    channel: aio_pika.abc.AbstractChannel
    callback_queue: aio_pika.abc.AbstractQueue
    exchange: aio_pika.abc.AbstractExchange
    loop: asyncio.AbstractEventLoop

    def __init__(self) -> None:
        """Initialize the class."""
        self.futures: MutableMapping[str, asyncio.Future] = {}

    async def connect(self) -> None:
        """Async callback for connection."""
        self.loop = asyncio.get_running_loop()
        self.connection = await aio_pika.connect_robust(
            host=SETTINGS.MQ_HOST,
            login=SETTINGS.MQ_USERNAME,
            password=SETTINGS.MQ_PASSWORD,
            virtualhost=SETTINGS.MQ_VIRTUAL_HOST,
            client_properties={"connection_name": socket.gethostname()},
            loop=self.loop,
        )
        self.channel = await self.connection.channel(publisher_confirms=True)
        self.exchange = await self.channel.get_exchange(SETTINGS.MQ_EXCHANGE, ensure=True)
        self.callback_queue = await self.channel.declare_queue(exclusive=True)
        await self.callback_queue.consume(self.on_response, no_ack=True)

    async def disconnect(self) -> None:
        """Async callback for disconnection."""
        await self.channel.close()
        await self.connection.close()

    async def on_response(self, message: aio_pika.abc.AbstractIncomingMessage) -> None:
        """Handle the response from the RPC server.

        If the message is not a response to a previous request, it will be logged and ignored.
        Otherwise, the response is stored in the `futures` dictionary and the future is
        resolved.
        """
        logger.debug("Received response from the RPC server")
        if message.correlation_id is None:
            logger.error(f"Bad message {message}")
            return

        future: asyncio.Future = self.futures.pop(message.correlation_id)
        future.set_result(message.body)

    async def call(self, message: bytes) -> Union[str, None]:
        """Publish a message to the exchange and waits for the response from the RPC server."""
        await self.connect()

        correlation_id = str(uuid.uuid4())
        future = self.loop.create_future()

        self.futures[correlation_id] = future

        logger.debug(
            "Publishing: {}".format(
                {
                    "exchange": self.exchange.name,
                    "message": message,
                }
            )
        )

        try:
            confirmation: aiormq.abc.ConfirmationFrameType | None = await self.exchange.publish(
                aio_pika.Message(
                    body=message,
                    correlation_id=correlation_id,
                    reply_to=self.callback_queue.name,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                timeout=SETTINGS.MQ_PUBLISH_TIMEOUT,
                routing_key="",  # the exchange is supposed to be fanout, so any value here is ignored
            )
        except DeliveryError as err:
            logger.error(f"Delivery of {message!r} failed: {err}")
            raise err
        except TimeoutError:
            logger.error(f"Timeout while publishing {message!r}")
            raise TimeoutError
        else:
            if not isinstance(confirmation, Basic.Ack):
                logger.error(f"Confirmation of {message!r} failed: {confirmation}")
                raise RuntimeError
            rpc_response: Union[bytes, None] = await future
        finally:
            await self.disconnect()

        return rpc_response.decode("utf-8") if rpc_response is not None else None


rabbitmq_manager = RabbitMQRpcClient()
