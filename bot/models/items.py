from pydantic import BaseModel, HttpUrl, Field


class ItemCard(BaseModel):
    chat_id: int
    query: str
    card_id: str
    description: str
    image_url: HttpUrl | None = None
    price: int = Field(ge=0)
    location_and_date: str
    item_url: HttpUrl


class ItemParams(BaseModel):
    card_id: str
    chat_id: int
    query: str
