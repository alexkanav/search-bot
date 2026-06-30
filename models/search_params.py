from pydantic import BaseModel, Field


class SearchParams(BaseModel):
    url: str
    query: str
    region: str | None = None
    location: str | None = None
    max_price: int | None = Field(default=None, ge=0)
    timeout: int | None = Field(default=None, ge=0)