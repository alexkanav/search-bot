from datetime import datetime, timedelta, UTC

from motor.motor_asyncio import AsyncIOMotorClient
from motor.motor_asyncio import AsyncIOMotorCollection

from models.item_card import ItemCard
from settings import Settings


class ItemRepository:
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._collection = collection

    async def get_items(self, user_id: int, query: str) -> list[ItemCard]:
        docs = await self._collection.find({"user_id": user_id, "query": query}).to_list(length=None)
        return [ItemCard.model_validate(doc) for doc in docs]

    async def get_item(self, user_id: int, card_id: str) -> ItemCard | None:
        doc = await self._collection.find_one({"user_id": user_id, "card_id": card_id})
        return ItemCard.model_validate(doc) if doc else None

    async def insert_items(self, user_id: int, items: list[ItemCard]) -> None:
        if not items:
            return

        expires_at = datetime.now(UTC) + timedelta(days=3)

        docs = [
            {
                "_id": f"{user_id}_{item.card_id}",
                "user_id": user_id,
                "expires_at": expires_at,
                **item.model_dump(mode="json")
            }
            for item in items
        ]

        await self._collection.insert_many(docs, ordered=False)


async def create_mongodb_repository(settings: Settings) -> tuple[ItemRepository, AsyncIOMotorClient]:
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGO_DB_NAME]

    collection = db[settings.MONGODB_COLLECTION]

    await collection.create_index(
        "expires_at",
        expireAfterSeconds=0,
    )
    return ItemRepository(collection), client
