"""Test the RabbitMQ ops manager."""
import asyncio
import time
from typing import Coroutine, Generator
from unittest import mock

import aio_pika
import pytest
from aiormq.exceptions import DeliveryError
from pamqp.commands import Basic

from api.broker_app.rpc_client import rabbitmq_manager
from api.settings import SETTINGS


@pytest.fixture
def rpc_response_message() -> Generator[str, None, None]:
    """Yield a dummy response message."""
    yield "RPC worked"


@pytest.fixture
def correlation_id() -> Generator[str, None, None]:
    """Yield an UUID4 example."""
    yield "f046711e-7d12-4250-a429-06845536f4f9"


@pytest.fixture
async def set_rpc_server_response(
    rpc_response_message: str, correlation_id: str
) -> Generator[aio_pika.Message, None, None]:
    """Yield a helper function to call the on_response method."""
    callback_message = aio_pika.Message(body=rpc_response_message.encode(), correlation_id=correlation_id)

    async def _helper() -> Coroutine:
        """Call the on_response method to set the RPC response in the future result.

        This is needed because the on_response method is asynchronously
        called by the RPC client after the RPC server sent a response.
        This is a workaround to get the RPC response in the future result.
        """
        # sleep to give time for the RPC client to execute its logic
        time.sleep(1)
        await rabbitmq_manager.on_response(callback_message)

    yield _helper


@pytest.mark.asyncio
@mock.patch("api.broker_app.rpc_client.aio_pika")
@mock.patch("api.broker_app.rpc_client.uuid")
async def test_publish_message_to_exchange__no_error_publishing_message(
    mocked_uuid: mock.Mock,
    mocked_aio_pika: mock.Mock,
    correlation_id: str,
    rpc_response_message: str,
    set_rpc_server_response: Coroutine,
):
    """Test if the class is able to publish messages to the broker and receive the response from the RPC server."""  # noqa: E501
    mocked_uuid.uuid4 = mock.Mock()
    mocked_uuid.uuid4.return_value = correlation_id

    mocked_exchange = mock.AsyncMock()
    mocked_exchange.name = "dummy-name"
    mocked_exchange.publish = mock.AsyncMock()
    mocked_exchange.publish.return_value = Basic.Ack(correlation_id)

    dummy_callback_queue_name = "dummy-callback-queue"
    mocked_callback_queue = mock.Mock()
    mocked_callback_queue.name = dummy_callback_queue_name
    mocked_callback_queue.consume = mock.AsyncMock()

    mocked_channel = mock.AsyncMock()
    mocked_channel.get_exchange = mock.AsyncMock()
    mocked_channel.get_exchange.return_value = mocked_exchange
    mocked_channel.declare_queue = mock.AsyncMock()
    mocked_channel.declare_queue.return_value = mocked_callback_queue

    mocked_connection = mock.AsyncMock()
    mocked_connection.close = mock.AsyncMock()
    mocked_connection.close.return_value = None
    mocked_connection.channel = mock.AsyncMock()
    mocked_connection.channel.return_value = mocked_channel

    mocked_aio_pika.connect_robust = mock.AsyncMock()
    mocked_aio_pika.connect_robust.return_value = mocked_connection

    mocked_aio_pika.ExchangeType = mock.Mock()
    mocked_aio_pika.ExchangeType.DIRECT = "DIRECT"

    mocked_aio_pika.DeliveryMode = mock.Mock()
    mocked_aio_pika.DeliveryMode.PERSISTENT = "PERSISTENT"

    mocked_aio_pika.Message = mock.Mock()
    mocked_aio_pika.Message.return_value = "Message"

    message = b"Test message"

    results = await asyncio.gather(*[rabbitmq_manager.call(message=message), set_rpc_server_response()])

    assert results[0] == rpc_response_message
    mocked_connection.close.assert_awaited_once_with()
    mocked_connection.channel.assert_awaited_once_with(publisher_confirms=True)
    mocked_channel.get_exchange.assert_awaited_once_with(SETTINGS.MQ_EXCHANGE, ensure=True)
    mocked_aio_pika.Message.assert_called_once_with(
        body=message,
        correlation_id=correlation_id,
        reply_to=dummy_callback_queue_name,
        delivery_mode=mocked_aio_pika.DeliveryMode.PERSISTENT,
    )
    mocked_exchange.publish.assert_awaited_once_with(
        mocked_aio_pika.Message(),
        timeout=SETTINGS.MQ_PUBLISH_TIMEOUT,
        routing_key="",
    )
    mocked_callback_queue.consume.assert_awaited_once()


@pytest.mark.asyncio
@mock.patch("api.broker_app.rpc_client.aio_pika")
@mock.patch("api.broker_app.rpc_client.uuid")
async def test_publish_message_to_exchange__check_delivery_error(
    mocked_uuid: mock.Mock, mocked_aio_pika: mock.Mock, caplog: pytest.LogCaptureFixture, correlation_id: str
):
    """Test if DeliveryError is raised when the broker fails to publish the message."""
    mocked_uuid.uuid4 = mock.Mock()
    mocked_uuid.uuid4.return_value = correlation_id

    mocked_exchange = mock.AsyncMock()
    mocked_exchange.name = "dummy-name"
    mocked_exchange.publish = mock.AsyncMock()
    mocked_exchange.publish.side_effect = aio_pika.exceptions.DeliveryError(
        "Something happened", frame=mock.Mock()
    )

    dummy_callback_queue_name = "dummy-callback-queue"
    mocked_callback_queue = mock.Mock()
    mocked_callback_queue.name = dummy_callback_queue_name
    mocked_callback_queue.consume = mock.AsyncMock()

    mocked_channel = mock.AsyncMock()
    mocked_channel.get_exchange = mock.AsyncMock()
    mocked_channel.get_exchange.return_value = mocked_exchange
    mocked_channel.declare_queue = mock.AsyncMock()
    mocked_channel.declare_queue.return_value = mocked_callback_queue

    mocked_connection = mock.AsyncMock()
    mocked_connection.close = mock.AsyncMock()
    mocked_connection.close.return_value = None
    mocked_connection.channel = mock.AsyncMock()
    mocked_connection.channel.return_value = mocked_channel

    mocked_aio_pika.connect_robust = mock.AsyncMock()
    mocked_aio_pika.connect_robust.return_value = mocked_connection

    mocked_aio_pika.ExchangeType = mock.Mock()
    mocked_aio_pika.ExchangeType.DIRECT = "DIRECT"

    mocked_aio_pika.DeliveryMode = mock.Mock()
    mocked_aio_pika.DeliveryMode.PERSISTENT = "PERSISTENT"

    mocked_aio_pika.Message = mock.Mock()
    mocked_aio_pika.Message.return_value = "Message"

    message = b"Test message"

    with pytest.raises(DeliveryError):
        await rabbitmq_manager.call(message=message)

    mocked_connection.close.assert_awaited_once_with()
    mocked_connection.channel.assert_awaited_once_with(publisher_confirms=True)
    mocked_channel.get_exchange.assert_awaited_once_with(SETTINGS.MQ_EXCHANGE, ensure=True)
    mocked_aio_pika.Message.assert_called_once_with(
        body=message,
        correlation_id=correlation_id,
        reply_to=dummy_callback_queue_name,
        delivery_mode=mocked_aio_pika.DeliveryMode.PERSISTENT,
    )
    mocked_exchange.publish.assert_awaited_once_with(
        mocked_aio_pika.Message(),
        timeout=SETTINGS.MQ_PUBLISH_TIMEOUT,
        routing_key="",
    )
    mocked_callback_queue.consume.assert_awaited_once()
    assert f"Delivery of {message} failed" in caplog.text


@pytest.mark.asyncio
@mock.patch("api.broker_app.rpc_client.aio_pika")
@mock.patch("api.broker_app.rpc_client.uuid")
async def test_publish_message_to_exchange__check_timeout_error(
    mocked_uuid: mock.Mock, mocked_aio_pika: mock.Mock, caplog: pytest.LogCaptureFixture, correlation_id: str
):
    """Test if TimeoutError is raised when the broker times out to publish the message."""
    mocked_uuid.uuid4 = mock.Mock()
    mocked_uuid.uuid4.return_value = correlation_id

    mocked_exchange = mock.AsyncMock()
    mocked_exchange.name = "dummy-name"
    mocked_exchange.publish = mock.AsyncMock()
    mocked_exchange.publish.side_effect = TimeoutError("Timed out")

    dummy_callback_queue_name = "dummy-callback-queue"
    mocked_callback_queue = mock.Mock()
    mocked_callback_queue.name = dummy_callback_queue_name
    mocked_callback_queue.consume = mock.AsyncMock()

    mocked_channel = mock.AsyncMock()
    mocked_channel.get_exchange = mock.AsyncMock()
    mocked_channel.get_exchange.return_value = mocked_exchange
    mocked_channel.declare_queue = mock.AsyncMock()
    mocked_channel.declare_queue.return_value = mocked_callback_queue

    mocked_connection = mock.AsyncMock()
    mocked_connection.close = mock.AsyncMock()
    mocked_connection.close.return_value = None
    mocked_connection.channel = mock.AsyncMock()
    mocked_connection.channel.return_value = mocked_channel

    mocked_aio_pika.connect_robust = mock.AsyncMock()
    mocked_aio_pika.connect_robust.return_value = mocked_connection

    mocked_aio_pika.ExchangeType = mock.Mock()
    mocked_aio_pika.ExchangeType.DIRECT = "DIRECT"

    mocked_aio_pika.DeliveryMode = mock.Mock()
    mocked_aio_pika.DeliveryMode.PERSISTENT = "PERSISTENT"

    mocked_aio_pika.Message = mock.Mock()
    mocked_aio_pika.Message.return_value = "Message"

    message = b"Test message"

    with pytest.raises(TimeoutError):
        await rabbitmq_manager.call(message=message)

    mocked_connection.close.assert_awaited_once_with()
    mocked_connection.channel.assert_awaited_once_with(publisher_confirms=True)
    mocked_channel.get_exchange.assert_awaited_once_with(SETTINGS.MQ_EXCHANGE, ensure=True)
    mocked_aio_pika.Message.assert_called_once_with(
        body=message,
        correlation_id=correlation_id,
        reply_to=dummy_callback_queue_name,
        delivery_mode=mocked_aio_pika.DeliveryMode.PERSISTENT,
    )
    mocked_exchange.publish.assert_awaited_once_with(
        mocked_aio_pika.Message(),
        timeout=SETTINGS.MQ_PUBLISH_TIMEOUT,
        routing_key="",
    )
    mocked_callback_queue.consume.assert_awaited_once()
    assert f"Timeout while publishing {message}" in caplog.text


@pytest.mark.asyncio
@mock.patch("api.broker_app.rpc_client.aio_pika")
@mock.patch("api.broker_app.rpc_client.uuid")
async def test_publish_message_to_exchange__check_no_error__check_no_ack(
    mocked_uuid: mock.Mock, mocked_aio_pika: mock.Mock, caplog: pytest.LogCaptureFixture, correlation_id: str
):
    """Test if TimeoutError is raised when the broker times out to publish the message."""
    mocked_uuid.uuid4 = mock.Mock()
    mocked_uuid.uuid4.return_value = correlation_id

    mocked_exchange = mock.AsyncMock()
    mocked_exchange.name = "dummy-name"
    mocked_exchange.publish = mock.AsyncMock()
    mocked_exchange.publish.return_value = Basic.Nack(delivery_tag=1, requeue=False)

    dummy_callback_queue_name = "dummy-callback-queue"
    mocked_callback_queue = mock.Mock()
    mocked_callback_queue.name = dummy_callback_queue_name
    mocked_callback_queue.consume = mock.AsyncMock()

    mocked_channel = mock.AsyncMock()
    mocked_channel.get_exchange = mock.AsyncMock()
    mocked_channel.get_exchange.return_value = mocked_exchange
    mocked_channel.declare_queue = mock.AsyncMock()
    mocked_channel.declare_queue.return_value = mocked_callback_queue

    mocked_connection = mock.AsyncMock()
    mocked_connection.close = mock.AsyncMock()
    mocked_connection.close.return_value = None
    mocked_connection.channel = mock.AsyncMock()
    mocked_connection.channel.return_value = mocked_channel

    mocked_aio_pika.connect_robust = mock.AsyncMock()
    mocked_aio_pika.connect_robust.return_value = mocked_connection

    mocked_aio_pika.ExchangeType = mock.Mock()
    mocked_aio_pika.ExchangeType.DIRECT = "DIRECT"

    mocked_aio_pika.DeliveryMode = mock.Mock()
    mocked_aio_pika.DeliveryMode.PERSISTENT = "PERSISTENT"

    mocked_aio_pika.Message = mock.Mock()
    mocked_aio_pika.Message.return_value = "Message"

    message = b"Test message"

    with pytest.raises(RuntimeError):
        await rabbitmq_manager.call(message=message)

    mocked_connection.close.assert_awaited_once_with()
    mocked_connection.channel.assert_awaited_once_with(publisher_confirms=True)
    mocked_channel.get_exchange.assert_awaited_once_with(SETTINGS.MQ_EXCHANGE, ensure=True)
    mocked_aio_pika.Message.assert_called_once_with(
        body=message,
        correlation_id=correlation_id,
        reply_to=dummy_callback_queue_name,
        delivery_mode=mocked_aio_pika.DeliveryMode.PERSISTENT,
    )
    mocked_exchange.publish.assert_awaited_once_with(
        mocked_aio_pika.Message(),
        timeout=SETTINGS.MQ_PUBLISH_TIMEOUT,
        routing_key="",
    )
    mocked_callback_queue.consume.assert_awaited_once()
    assert f"Confirmation of {message} failed" in caplog.text


@pytest.mark.asyncio
async def test_on_response_callback_method(rpc_response_message: str, caplog: pytest.LogCaptureFixture):
    """Test how the on_response callback method consumes the message from the RPC server."""
    callback_message = aio_pika.Message(body=rpc_response_message.encode(), correlation_id=None)

    result = await rabbitmq_manager.on_response(callback_message)

    assert f"Bad message {callback_message}" in caplog.text
    assert result is None
