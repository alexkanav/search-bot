import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from playwright.async_api import async_playwright

from infrastructure.logging_config import configure_logging
from infrastructure.mongo_repository import create_mongodb_repository
from infrastructure.redis import get_redis_client
from scraper.marketplace_scraper import MarketplaceScraper
from services.task_manager import TaskManager
from settings import Settings
from telegram.handlers.commands import router as common_router
from telegram.handlers.database import router as database_router
from telegram.handlers.items import router as item_router
from telegram.handlers.scraper import router as scraper_router
from telegram.middlewares import ServicesMiddleware
from telegram.setup_commands import set_commands


async def main() -> None:
    settings = Settings()

    configure_logging(settings.LOG_FILE_PATH)

    redis = await get_redis_client(settings.redis_url)
    storage = RedisStorage(redis) if redis else MemoryStorage()

    bot = Bot(token=settings.TOKEN)
    dp = Dispatcher(storage=storage)

    playwright = await async_playwright().start()

    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ],
    )

    scraper = MarketplaceScraper(browser, redis)

    repository, mongo_client = await create_mongodb_repository(settings)

    task_manager = TaskManager()

    middleware = ServicesMiddleware(
        repository=repository,
        scraper=scraper,
        task_manager=task_manager,
    )

    dp.message.middleware(middleware)
    dp.callback_query.middleware(middleware)

    dp.include_router(common_router)
    dp.include_router(item_router)
    dp.include_router(scraper_router)
    dp.include_router(database_router)

    await set_commands(bot)
    await bot.delete_webhook(drop_pending_updates=True)

    try:
        await dp.start_polling(bot)

    finally:
        mongo_client.close()
        await browser.close()
        await playwright.stop()

        if redis:
            await redis.aclose()

        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
