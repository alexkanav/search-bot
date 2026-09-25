from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock

import pytest

from config import ITEM_TTL_DAYS
from infrastructure.mongo_repository import ItemRepository, create_mongodb_repository
from models.items import ItemCard


@pytest.mark.asyncio
async def test_get_items__matching_documents__returns_item_cards(make_item):
    item1 = make_item(card_id="12")
    item2 = make_item(card_id="14")
    collection = MagicMock()

    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=[
        item1.model_dump(mode="json"),
        item2.model_dump(mode="json"),
    ])

    collection.find.return_value = cursor

    repository = ItemRepository(collection)

    result = await repository.get_items(
        user_id=123,
        query="iphone",
    )

    collection.find.assert_called_once_with(
        {
            "user_id": 123,
            "query": "iphone",
        }
    )

    cursor.to_list.assert_awaited_once_with(length=None)

    assert len(result) == 2
    assert all(isinstance(item, ItemCard) for item in result)
    assert result[0].card_id == "12"
    assert result[1].card_id == "14"


@pytest.mark.asyncio
async def test_get_items__no_documents__returns_empty_list():
    collection = MagicMock()

    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=[])

    collection.find.return_value = cursor

    repository = ItemRepository(collection)

    result = await repository.get_items(
        user_id=456,
        query="iphone",
    )

    assert result == []

    collection.find.assert_called_once_with(
        {
            "user_id": 456,
            "query": "iphone",
        }
    )


@pytest.mark.asyncio
async def test_get_item__document_exists__returns_item(make_item):
    item = make_item()
    collection = MagicMock()

    collection.find_one = AsyncMock(
        return_value=item.model_dump(mode="json")
    )

    repository = ItemRepository(collection)

    result = await repository.get_item(
        user_id=123,
        card_id="card-1",
    )

    collection.find_one.assert_awaited_once_with(
        {
            "user_id": 123,
            "card_id": "card-1",
        }
    )

    assert len(result) == 1
    assert isinstance(result[0], ItemCard)
    assert result[0].card_id == "card-1"


@pytest.mark.asyncio
async def test_get_item__document_not_found__returns_empty_list():
    collection = MagicMock()
    collection.find_one = AsyncMock(return_value=None)

    repository = ItemRepository(collection)

    result = await repository.get_item(
        user_id=456,
        card_id="123",
    )

    assert result == []

    collection.find_one.assert_awaited_once_with(
        {
            "user_id": 456,
            "card_id": "123",
        }
    )


@pytest.mark.asyncio
async def test_insert_items__empty_list__does_nothing():
    collection = MagicMock()
    collection.insert_many = AsyncMock()

    repository = ItemRepository(collection)

    await repository.insert_items(
        user_id=456,
        items=[],
    )

    collection.insert_many.assert_not_awaited()


@pytest.mark.asyncio
async def test_insert_items__items_provided__inserts_documents(make_item):
    item1 = make_item(card_id="10", chat_id=456)
    item2 = make_item(card_id="20", chat_id=456)

    collection = MagicMock()
    collection.insert_many = AsyncMock()

    repository = ItemRepository(collection)
    items = [item1, item2]
    await repository.insert_items(
        user_id=456,
        items=items,
    )

    collection.insert_many.assert_awaited_once()

    docs = collection.insert_many.await_args.args[0]

    assert len(docs) == 2

    assert docs[0]["_id"] == "456_10"
    assert docs[0]["user_id"] == 456
    assert docs[0]["card_id"] == "10"

    assert docs[1]["_id"] == "456_20"
    assert docs[1]["user_id"] == 456
    assert docs[1]["card_id"] == "20"

    assert isinstance(docs[0]["expires_at"], datetime)
    assert isinstance(docs[1]["expires_at"], datetime)

    collection.insert_many.assert_awaited_once_with(
        docs,
        ordered=False,
    )


@pytest.mark.asyncio
async def test_insert_items__items_provided__sets_expiration_date(make_item):
    item = make_item()
    collection = MagicMock()
    collection.insert_many = AsyncMock()

    repository = ItemRepository(collection)

    before = datetime.now(UTC)

    await repository.insert_items(
        user_id=123,
        items=[item],
    )

    after = datetime.now(UTC)

    docs = collection.insert_many.await_args.args[0]

    expires_at = docs[0]["expires_at"]

    assert before + timedelta(days=ITEM_TTL_DAYS) <= expires_at <= after + timedelta(days=ITEM_TTL_DAYS)


@pytest.mark.asyncio
async def test_create_mongodb_repository__valid_settings__creates_repository(mocker):
    mock_client_class = mocker.patch("infrastructure.mongo_repository.AsyncIOMotorClient")
    client = MagicMock()
    db = MagicMock()
    collection = MagicMock()

    mock_client_class.return_value = client
    client.__getitem__.return_value = db
    db.__getitem__.return_value = collection

    collection.create_index = AsyncMock()

    settings = MagicMock()
    settings.MONGODB_URL = "mongodb://localhost:27017"
    settings.MONGO_DB_NAME = "marketplace"
    settings.MONGODB_COLLECTION = "items"

    repository, result_client = await create_mongodb_repository(settings)

    mock_client_class.assert_called_once_with(
        "mongodb://localhost:27017",
    )

    client.__getitem__.assert_called_once_with(
        "marketplace",
    )

    db.__getitem__.assert_called_once_with(
        "items",
    )

    collection.create_index.assert_awaited_once_with(
        "expires_at",
        expireAfterSeconds=0,
    )

    assert isinstance(repository, ItemRepository)
    assert repository._collection is collection
    assert result_client is client


@pytest.mark.asyncio
async def test_create_mongodb_repository__index_creation_fails__raises_error(
        mocker,
):
    mock_client_class = mocker.patch("infrastructure.mongo_repository.AsyncIOMotorClient")

    client = MagicMock()
    db = MagicMock()
    collection = MagicMock()

    mock_client_class.return_value = client
    client.__getitem__.return_value = db
    db.__getitem__.return_value = collection

    collection.create_index = mocker.AsyncMock(
        side_effect=RuntimeError("MongoDB unavailable"),
    )

    settings = MagicMock()
    settings.MONGODB_URL = "mongodb://localhost:27017"
    settings.MONGO_DB_NAME = "marketplace"
    settings.MONGODB_COLLECTION = "items"

    with pytest.raises(RuntimeError, match="MongoDB unavailable"):
        await create_mongodb_repository(settings)
