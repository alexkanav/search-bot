import asyncio
import logging

from aiogram.types import Message

from infrastructure.mongo_repository import ItemRepository
from models.search_params import SearchParams
from scraper.marketplace_scraper import MarketplaceScraper
from services.telegram_service import notify_user

logger = logging.getLogger(__name__)


async def process_new_items(
        repository: ItemRepository,
        scraper: MarketplaceScraper,
        message: Message,
        search_params: SearchParams
) -> None:
    user_id = message.from_user.id
    new_items = await scraper.find_new_items(user_id, search_params)
    if not new_items:
        return

    for item in new_items:
        await notify_user(message, item)

    await repository.insert_items(user_id, new_items)


async def run_monitoring(
        repository: ItemRepository,
        scraper: MarketplaceScraper,
        message: Message,
        search_params: SearchParams
) -> None:
    user_id = message.from_user.id

    try:
        if not search_params.timeout:
            await process_new_items(repository, scraper, message, search_params)
            return

        while True:
            await process_new_items(repository, scraper, message, search_params)

            await asyncio.sleep(search_params.timeout * 60)

    except asyncio.CancelledError:
        logger.info("Stopped monitoring user %s", user_id)
        raise
