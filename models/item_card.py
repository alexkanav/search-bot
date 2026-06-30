from pydantic import BaseModel, HttpUrl, Field


class ItemCard(BaseModel):
    query: str
    card_id: str
    description: str
    image_url: HttpUrl
    price: int = Field(ge=0)
    location_and_date: str
    item_url: HttpUrl
