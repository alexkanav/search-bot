import json
from unittest.mock import AsyncMock, MagicMock

import aio_pika
import pytest

from infrastructure.rabbitmq import RabbitMQ


@pytest.fixture
def rabbitmq():
    return RabbitMQ("amqp://guest:guest@localhost/")


def test_init__creates_rabbitmq():
    rabbitmq = RabbitMQ("amqp://localhost")

    assert rabbitmq.url == "amqp://localhost"
    assert rabbitmq.connection is None
    assert rabbitmq.channel is None


@pytest.mark.asyncio
async def test_connect__successful__stores_connection_and_channel(
        mocker,
        rabbitmq,
):
    mock_connect = mocker.patch(
        "infrastructure.rabbitmq.aio_pika.connect_robust"
    )
    connection = AsyncMock()
    channel = AsyncMock()

    mock_connect.return_value = connection
    connection.channel.return_value = channel

    await rabbitmq.connect()

    mock_connect.assert_awaited_once_with(
        "amqp://guest:guest@localhost/"
    )
    connection.channel.assert_awaited_once()

    assert rabbitmq.connection is connection
    assert rabbitmq.channel is channel


@pytest.mark.asyncio
async def test_connect__connection_failure__raises_error(
        mocker,
        rabbitmq,
):
    mock_connect = mocker.patch("infrastructure.rabbitmq.aio_pika.connect_robust")
    mock_connect.side_effect = ConnectionError("RabbitMQ unavailable")

    with pytest.raises(
            ConnectionError,
            match="RabbitMQ unavailable",
    ):
        await rabbitmq.connect()

    assert rabbitmq.connection is None
    assert rabbitmq.channel is None


@pytest.mark.asyncio
async def test_connect__channel_creation_failure__raises_error(
        mocker,
        rabbitmq,
):
    mock_connect = mocker.patch(
        "infrastructure.rabbitmq.aio_pika.connect_robust"
    )

    connection = AsyncMock()
    connection.channel.side_effect = ConnectionError(
        "Channel unavailable"
    )
    mock_connect.return_value = connection

    with pytest.raises(
            ConnectionError,
            match="Channel unavailable",
    ):
        await rabbitmq.connect()

    assert rabbitmq.connection is connection
    assert rabbitmq.channel is None


@pytest.mark.asyncio
async def test_consume__queue__declares_durable_queue(rabbitmq):
    channel = AsyncMock()
    queue = AsyncMock()

    rabbitmq.channel = channel
    channel.declare_queue.return_value = queue
    queue.consume.return_value = "consumer-tag"

    callback = AsyncMock()

    result = await rabbitmq.consume(
        "search_result",
        callback,
    )

    assert result == "consumer-tag"

    channel.declare_queue.assert_awaited_once_with(
        "search_result",
        durable=True,
    )


@pytest.mark.asyncio
async def test_consume__message_received__calls_callback(
        rabbitmq,
):
    channel = AsyncMock()
    queue = AsyncMock()

    rabbitmq.channel = channel
    channel.declare_queue.return_value = queue
    queue.consume.return_value = "consumer-tag"

    callback = AsyncMock()

    message = MagicMock()

    process_context = AsyncMock()
    message.process.return_value = process_context

    await rabbitmq.consume(
        "search_result",
        callback,
    )

    handler = queue.consume.call_args.args[0]

    await handler(message)

    message.process.assert_called_once_with()
    process_context.__aenter__.assert_awaited_once()
    process_context.__aexit__.assert_awaited_once()
    callback.assert_awaited_once_with(message)


@pytest.mark.asyncio
async def test_consume__args_and_kwargs__passes_them_to_callback(
        rabbitmq,
):
    channel = AsyncMock()
    queue = AsyncMock()

    rabbitmq.channel = channel
    channel.declare_queue.return_value = queue

    callback = AsyncMock()

    message = MagicMock()

    process_context = AsyncMock()
    message.process.return_value = process_context

    await rabbitmq.consume(
        "search_result",
        callback,
        "argument",
        user_id=123,
    )

    handler = queue.consume.call_args.args[0]

    await handler(message)
    message.process.assert_called_once_with()

    callback.assert_awaited_once_with(
        message,
        "argument",
        user_id=123,
    )


@pytest.mark.asyncio
async def test_publish__valid_body__publishes_persistent_json_message(
        mocker,
        rabbitmq,
):
    mock_message_class = mocker.patch(
        "infrastructure.rabbitmq.aio_pika.Message"
    )
    exchange = AsyncMock()
    channel = MagicMock()
    channel.default_exchange = exchange

    rabbitmq.channel = channel

    body = {
        "chat_id": 123,
        "query": "iphone",
        "price": 1000,
    }

    message = MagicMock()
    mock_message_class.return_value = message

    await rabbitmq.publish("search_request", body)

    kwargs = mock_message_class.call_args.kwargs

    assert json.loads(kwargs["body"].decode()) == body
    assert kwargs["delivery_mode"] == aio_pika.DeliveryMode.PERSISTENT

    exchange.publish.assert_awaited_once_with(
        message,
        routing_key="search_request",
    )


@pytest.mark.asyncio
async def test_close__connected__closes_and_resets_state(
        rabbitmq,
):
    connection = AsyncMock()
    channel = AsyncMock()

    rabbitmq.connection = connection
    rabbitmq.channel = channel

    await rabbitmq.close()

    connection.close.assert_awaited_once()

    assert rabbitmq.connection is None
    assert rabbitmq.channel is None


@pytest.mark.asyncio
async def test_close__not_connected__does_nothing(
        rabbitmq,
):
    await rabbitmq.close()

    assert rabbitmq.connection is None
    assert rabbitmq.channel is None
