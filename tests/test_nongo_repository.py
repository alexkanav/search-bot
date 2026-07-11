from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from infrastructure.mongo_repository import ItemRepository, create_mongodb_repository
from models.item_card import ItemCard


@pytest.fixture
def collection():
    return MagicMock()


@pytest.fixture
def repository(collection):
    return ItemRepository(collection)


@pytest.fixture
def item():
    return ItemCard(
        query="iphone",
        card_id="123",
        description="iPhone 15",
        image_url="https://example.com/image.jpg",
        price=1000,
        location_and_date="Kyiv",
        item_url="https://example.com/item",
    )


@pytest.mark.asyncio
async def test_get_items__items_exist__returns_item_list(repository, collection, item):
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=[item.model_dump(mode="json")])

    collection.find.return_value = cursor

    result = await repository.get_items(user_id=1, query="iphone")

    collection.find.assert_called_once_with(
        {"user_id": 1, "query": "iphone"}
    )
    cursor.to_list.assert_awaited_once_with(length=None)

    assert result == [item]


@pytest.mark.asyncio
async def test_get_items__no_items_exist__returns_empty_list(repository, collection):
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=[])

    collection.find.return_value = cursor

    result = await repository.get_items(1, "iphone")

    assert result == []
    collection.find.assert_called_once_with(
        {"user_id": 1, "query": "iphone"}
    )
    cursor.to_list.assert_awaited_once_with(length=None)


@pytest.mark.asyncio
async def test_get_item__item_exists__returns_item(repository, collection, item):
    collection.find_one = AsyncMock(
        return_value=item.model_dump(mode="json")
    )

    result = await repository.get_item(1, "123")

    collection.find_one.assert_awaited_once_with(
        {"user_id": 1, "card_id": "123"}
    )

    assert result == item


@pytest.mark.asyncio
async def test_get_item__item_does_not_exist__returns_none(repository, collection):
    collection.find_one = AsyncMock(return_value=None)

    result = await repository.get_item(1, "123")

    collection.find_one.assert_awaited_once_with(
        {"user_id": 1, "card_id": "123"}
    )

    assert result is None


@pytest.mark.asyncio
async def test_insert_items__items_provided__inserts_documents(repository, collection, item):
    collection.insert_many = AsyncMock()

    before = datetime.now(UTC)

    await repository.insert_items(1, [item])

    after = datetime.now(UTC)

    collection.insert_many.assert_awaited_once()

    docs = collection.insert_many.await_args.args[0]
    ordered = collection.insert_many.await_args.kwargs["ordered"]

    assert ordered is False
    assert len(docs) == 1

    doc = docs[0]

    assert doc["_id"] == "1_123"
    assert doc["user_id"] == 1
    assert doc["query"] == item.query
    assert doc["card_id"] == item.card_id
    assert doc["description"] == item.description
    assert doc["price"] == item.price
    assert doc["location_and_date"] == item.location_and_date
    assert doc["image_url"] == str(item.image_url)
    assert doc["item_url"] == str(item.item_url)

    assert before + timedelta(days=3) <= doc["expires_at"] <= after + timedelta(days=3)


@pytest.mark.asyncio
async def test_insert_items__empty_list__does_not_insert_documents(repository, collection):
    collection.insert_many = AsyncMock()

    await repository.insert_items(1, [])

    collection.insert_many.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_mongodb_repository__valid_settings__returns_repository_and_client(mocker):
    client_cls = mocker.patch(
        "infrastructure.mongo_repository.AsyncIOMotorClient"
    )
    settings = MagicMock()
    settings.MONGODB_URL = "mongodb://localhost"
    settings.MONGO_DB_NAME = "db"
    settings.MONGODB_COLLECTION = "items"

    client = MagicMock()
    db = MagicMock()
    collection = MagicMock()

    collection.create_index = AsyncMock()

    client.__getitem__.return_value = db
    db.__getitem__.return_value = collection
    client_cls.return_value = client

    repository, returned_client = await create_mongodb_repository(settings)

    assert isinstance(repository, ItemRepository)
    assert returned_client is client

    collection.create_index.assert_awaited_once_with(
        "expires_at",
        expireAfterSeconds=0,
    )
    client_cls.assert_called_once_with("mongodb://localhost")

    assert repository._collection is collection
