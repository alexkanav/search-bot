from unittest.mock import AsyncMock, MagicMock

import pytest

from main import main
from services.notification_service import notify_user


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "polling_error",
    [
        None,
        RuntimeError("polling failed"),
    ],
    ids=["success", "failure"],
)
async def test_main__polling__closes_resources(mocker, polling_error):
    redis_client = AsyncMock()
    rabbitmq = AsyncMock()
    bot = AsyncMock()

    settings = MagicMock(
        redis_url="redis://localhost",
        TOKEN="token",
        RABBITMQ_URL="amqp://localhost",
        SEARCH_SERVICE_URL="http://search-service",
        SERVICE_TOKEN="service-token",
        log_file_path="app.log",
    )

    mocker.patch("main.Settings", return_value=settings)
    mocker.patch("main.configure_logging")
    mocker.patch("main.create_redis_client", return_value=redis_client)
    mocker.patch("main.Bot", return_value=bot)
    mocker.patch("main.RabbitMQ", return_value=rabbitmq)
    mock_search_service = mocker.patch("main.SearchService")
    mocker.patch("main.set_commands")
    mocker.patch("main.common_router")
    mocker.patch("main.item_router")
    mocker.patch("main.collector_router")
    mocker.patch("main.database_router")

    dispatcher_class = mocker.patch("main.Dispatcher")
    dp = dispatcher_class.return_value

    dp.start_polling = AsyncMock(side_effect=polling_error)

    if polling_error:
        with pytest.raises(RuntimeError, match="polling failed"):
            await main()
    else:
        await main()

    dp.start_polling.assert_awaited_once_with(bot)

    rabbitmq.connect.assert_awaited_once()
    rabbitmq.consume.assert_awaited_once_with(
        "search_result",
        notify_user,
        bot,
    )
    mock_search_service.assert_called_once_with(
        base_url=settings.SEARCH_SERVICE_URL,
        token=settings.SERVICE_TOKEN,
        redis=redis_client,
    )
    rabbitmq.close.assert_awaited_once()

    redis_client.aclose.assert_awaited_once()

    bot.session.close.assert_awaited_once()
