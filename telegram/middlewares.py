from collections.abc import Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from infrastructure.mongo_repository import ItemRepository
from scraper.marketplace_scraper import MarketplaceScraper
from services.task_manager import TaskManager


class ServicesMiddleware(BaseMiddleware):
    def __init__(self, repository: ItemRepository, scraper: MarketplaceScraper, task_manager: TaskManager) -> None:
        self.repository = repository
        self.scraper = scraper
        self.task_manager = task_manager

    async def __call__(self, handler: Callable, event: TelegramObject, data: dict[str, Any]) -> Any:
        data["repository"] = self.repository
        data["scraper"] = self.scraper
        data["task_manager"] = self.task_manager
        return await handler(event, data)
