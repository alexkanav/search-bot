from unittest.mock import AsyncMock

import pytest
from redis.exceptions import RedisError

from infrastructure.redis import create_redis_client


@pytest.mark.asyncio
async def test_create_redis_client__successful_ping__returns_client(mocker):
    client = AsyncMock()
    mock_from_url = mocker.patch(
        "infrastructure.redis.Redis.from_url",
        return_value=client,
    )

    result = await create_redis_client(
        "redis://localhost:6379",
    )

    mock_from_url.assert_called_once_with(
        "redis://localhost:6379",
        socket_connect_timeout=3,
        socket_timeout=3,
    )
    client.ping.assert_awaited_once()

    assert result is client


@pytest.mark.asyncio
async def test_create_redis_client__redis_error__closes_client_and_returns_none(
        mocker,
):
    client = AsyncMock()
    mock_from_url = mocker.patch(
        "infrastructure.redis.Redis.from_url",
        return_value=client,
    )

    client.ping.side_effect = RedisError()
    mock_logger = mocker.patch("infrastructure.redis.logger")

    result = await create_redis_client(
        "redis://localhost:6379",
    )

    mock_from_url.assert_called_once_with(
        "redis://localhost:6379",
        socket_connect_timeout=3,
        socket_timeout=3,
    )

    client.ping.assert_awaited_once()
    client.aclose.assert_awaited_once()
    mock_logger.warning.assert_called_once_with("Redis unavailable", exc_info=True)

    assert result is None


@pytest.mark.asyncio
async def test_create_redis_client__unexpected_error__closes_client_and_returns_none(
        mocker,
):
    client = AsyncMock()
    mock_from_url = mocker.patch(
        "infrastructure.redis.Redis.from_url",
        return_value=client,
    )

    client.ping.side_effect = RuntimeError("unexpected error")

    mock_logger = mocker.patch("infrastructure.redis.logger")

    result = await create_redis_client(
        "redis://localhost:6379",
    )

    mock_from_url.assert_called_once_with(
        "redis://localhost:6379",
        socket_connect_timeout=3,
        socket_timeout=3,
    )

    client.ping.assert_awaited_once()
    client.aclose.assert_awaited_once()

    mock_logger.exception.assert_called_once_with("Unexpected error during Redis initialization")

    assert result is None


@pytest.mark.asyncio
async def test_create_redis_client__initialization_error__returns_none(
        mocker,
):
    mock_from_url = mocker.patch(
        "infrastructure.redis.Redis.from_url",
        side_effect=RuntimeError("cannot create client"),
    )

    mock_logger = mocker.patch("infrastructure.redis.logger")

    result = await create_redis_client(
        "redis://localhost:6379",
    )

    assert result is None
    mock_from_url.assert_called_once_with(
        "redis://localhost:6379",
        socket_connect_timeout=3,
        socket_timeout=3,
    )

    mock_logger.exception.assert_called_once_with("Unexpected error during Redis initialization")
