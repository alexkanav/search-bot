from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, Request

from models.locations import LocationsRequest, LocationsResponse
from models.regions import RegionRequest, RegionsResponse
from routes import fetch_regions, fetch_locations, get_scraper, verify_token, TOKEN


@pytest.mark.asyncio
async def test_verify_token__correct_token__returns_none():
    authorization = f"Bearer {TOKEN}"

    result = await verify_token(authorization)

    assert result is None


@pytest.mark.asyncio
async def test_verify_token__incorrect_token__raises_401():
    with pytest.raises(HTTPException) as exc_info:
        await verify_token("Bearer wrong-token")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Unauthorized"


@pytest.mark.asyncio
async def test_verify_token__missing_bearer_prefix__raises_401():
    with pytest.raises(HTTPException) as exc_info:
        await verify_token(TOKEN)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Unauthorized"


def test_get_scraper__scraper_in_app_state__returns_scraper():
    scraper = MagicMock()
    request = MagicMock(spec=Request)

    request.app.state.scraper = scraper

    assert get_scraper(request) is scraper


@pytest.mark.asyncio
async def test_fetch_regions__scraper_returns_regions__returns_response():
    scraper = MagicMock()
    scraper.get_regions = AsyncMock(
        return_value=["Kyiv", "Lviv"]
    )

    data = RegionRequest(
        url="https://example.com"
    )

    result = await fetch_regions(
        data=data,
        scraper=scraper,
    )

    assert isinstance(result, RegionsResponse)
    assert result.regions == ["Kyiv", "Lviv"]

    scraper.get_regions.assert_awaited_once_with(
        data.url
    )


@pytest.mark.asyncio
async def test_fetch_regions__scraper_returns_empty_list__returns_empty_response():
    scraper = MagicMock()
    scraper.get_regions = AsyncMock(return_value=[])

    data = RegionRequest(url="https://example.com")

    result = await fetch_regions(
        data=data,
        scraper=scraper,
    )

    assert isinstance(result, RegionsResponse)
    assert result.regions == []
    scraper.get_regions.assert_awaited_once_with(data.url)


@pytest.mark.asyncio
async def test_fetch_locations__scraper_returns_locations__returns_response():
    scraper = MagicMock()
    scraper.get_locations = AsyncMock(
        return_value=["Kherson", "Skadovsk"]
    )

    data = LocationsRequest(
        region="Kherson",
        url="https://example.com",
    )

    result = await fetch_locations(
        data=data,
        scraper=scraper,
    )

    assert isinstance(result, LocationsResponse)
    assert result.locations == ["Kherson", "Skadovsk"]

    scraper.get_locations.assert_awaited_once_with(
        data.region,
        data.url,
    )


@pytest.mark.asyncio
async def test_fetch_locations__scraper_returns_empty_list__returns_empty_response():
    scraper = MagicMock()
    scraper.get_locations = AsyncMock(return_value=[])

    data = LocationsRequest(
        region="Kherson",
        url="https://example.com",
    )

    result = await fetch_locations(
        data=data,
        scraper=scraper,
    )
    assert isinstance(result, LocationsResponse)
    assert result.locations == []
    scraper.get_locations.assert_awaited_once_with(
        data.region,
        data.url,
    )
