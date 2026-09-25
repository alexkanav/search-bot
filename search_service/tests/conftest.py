from typing import Any, Callable
from unittest.mock import MagicMock

import pytest

from infrastructure.mongo_repository import ItemRepository
from infrastructure.rabbitmq import RabbitMQ
from models.items import ItemCard
from models.search import SearchParams
from scraper.marketplace_scraper import MarketplaceScraper
from services.search_control import SearchService
from services.task_manager import TaskManager
from utils.enums import Command


@pytest.fixture
def make_search_params() -> Callable[..., SearchParams]:
    def factory(**kwargs: Any) -> SearchParams:
        defaults = {
            "command": Command.START,
            "chat_id": 123,
            "url": "https://example.com/search",
            "query": "iphone",
            "region": "Kyiv",
            "location": "Kyiv",
            "max_price": 1000,
            "timeout": None,
        }
        return SearchParams.model_validate(defaults | kwargs)

    return factory


@pytest.fixture
def make_item(make_search_params: Callable[..., SearchParams]) -> Callable[..., ItemCard]:
    def factory(**kwargs: Any) -> ItemCard:
        params = make_search_params()

        defaults = {
            "chat_id": params.chat_id,
            "query": params.query,
            "card_id": "card-1",
            "description": "iPhone 15",
            "image_url": "https://example.com",
            "price": 800,
            "location_and_date": "Kyiv, today",
            "item_url": "https://example.com",
        }

        return ItemCard.model_validate(defaults | kwargs)

    return factory


@pytest.fixture
def search_service() -> SearchService:
    return SearchService(
        repository=MagicMock(spec=ItemRepository),
        scraper=MagicMock(spec=MarketplaceScraper),
        rabbit=MagicMock(spec=RabbitMQ),
        task_manager=MagicMock(spec=TaskManager),
    )
