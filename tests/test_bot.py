from unittest.mock import AsyncMock, MagicMock

import pytest

from bot import main


@pytest.fixture
def settings(mocker):
    settings = MagicMock(
        TOKEN="token",
        LOG_FILE_PATH="bot.log",
        redis_url="redis://localhost",
    )
    mocker.patch("bot.Settings", return_value=settings)
    return settings


@pytest.mark.parametrize("use_redis", [True, False], ids=["redis_storage", "memory_storage"])
@pytest.mark.asyncio
async def test_main__valid_configuration__initializes_and_shuts_down_resources(use_redis, mocker, settings):
    redis = AsyncMock() if use_redis else None

    configure_logging = mocker.patch("bot.configure_logging")

    get_redis_client = mocker.patch(
        "bot.get_redis_client",
        AsyncMock(return_value=redis),
    )

    redis_storage = MagicMock()
    memory_storage = MagicMock()
    redis_storage_cls = mocker.patch(
        "bot.RedisStorage",
        return_value=redis_storage,
    )
    memory_storage_cls = mocker.patch(
        "bot.MemoryStorage",
        return_value=memory_storage,
    )

    bot = AsyncMock()
    bot.session.close = AsyncMock()
    bot.delete_webhook = AsyncMock()

    bot_cls = mocker.patch(
        "bot.Bot",
        return_value=bot,
    )

    dispatcher = AsyncMock()
    dispatcher.message.middleware = MagicMock()
    dispatcher.callback_query.middleware = MagicMock()
    dispatcher.include_router = MagicMock()
    dispatcher.start_polling = AsyncMock()
    dispatcher_cls = mocker.patch(
        "bot.Dispatcher",
        return_value=dispatcher,
    )

    browser = AsyncMock()

    playwright = AsyncMock()
    playwright.chromium.launch.return_value = browser
    playwright.stop = AsyncMock()
    playwright_context = MagicMock()
    playwright_context.start = AsyncMock(return_value=playwright)

    mocker.patch(
        "bot.async_playwright",
        return_value=playwright_context,
    )

    repository = MagicMock()
    mongo_client = MagicMock()

    create_repo = mocker.patch(
        "bot.create_mongodb_repository",
        AsyncMock(return_value=(repository, mongo_client)),
    )

    set_commands = mocker.patch(
        "bot.set_commands",
        AsyncMock(),
    )

    await main()

    configure_logging.assert_called_once_with(settings.LOG_FILE_PATH)

    get_redis_client.assert_awaited_once_with(settings.redis_url)

    if use_redis:
        redis_storage_cls.assert_called_once_with(redis)
        memory_storage_cls.assert_not_called()
        redis.aclose.assert_awaited_once()
    else:
        memory_storage_cls.assert_called_once()
        redis_storage_cls.assert_not_called()

    bot_cls.assert_called_once_with(token=settings.TOKEN)
    dispatcher_cls.assert_called_once()

    playwright_context.start.assert_awaited_once()
    playwright.chromium.launch.assert_awaited_once()

    create_repo.assert_awaited_once_with(settings)

    dispatcher.message.middleware.assert_called_once()
    dispatcher.callback_query.middleware.assert_called_once()

    assert dispatcher.include_router.call_count == 4

    set_commands.assert_awaited_once_with(bot)
    bot.delete_webhook.assert_awaited_once_with(
        drop_pending_updates=True
    )

    dispatcher.start_polling.assert_awaited_once_with(bot)

    mongo_client.close.assert_called_once()
    browser.close.assert_awaited_once()
    playwright.stop.assert_awaited_once()
    bot.session.close.assert_awaited_once()
