import json
from typing import Callable
from unittest.mock import MagicMock, AsyncMock

import httpx
import pytest
from redis.exceptions import RedisError

from config import CACHE_TTL
from models.locations import LocationsRequest, LocationsResponse
from models.regions import RegionsRequest, RegionsResponse
from services.search_service import SearchService


@pytest.fixture
def make_search_service() -> Callable[..., SearchService]:
    def factory(**kwargs) -> SearchService:
        defaults = {
            "base_url": "http://search-service:8000",
            "token": "test-token",
            "redis": None,
        }
        return SearchService(**(defaults | kwargs))

    return factory


def test_init__valid_data__stores_configuration(make_search_service):
    service = make_search_service()

    assert service.base_url == "http://search-service:8000"
    assert service.token == "test-token"
    assert service.redis is None


@pytest.mark.asyncio
async def test_post_json__successful_response__returns_model(mocker, make_search_service):
    mock_post = mocker.patch("services.search_service.httpx.AsyncClient.post")

    mock_response = MagicMock()
    mock_response.json.return_value = {"regions": ["Kyiv", "Lviv"]}
    mock_post.return_value = mock_response

    service = make_search_service()
    payload = RegionsRequest(url="http://marketplace.com")

    result = await service.post_json(
        "/regions",
        payload,
        RegionsResponse,
    )

    assert result == RegionsResponse(regions=["Kyiv", "Lviv"])

    mock_post.assert_awaited_once_with(
        "http://search-service:8000/regions",
        json={"url": "http://marketplace.com/"},
        headers={"Authorization": "Bearer test-token"},
    )
    mock_response.raise_for_status.assert_called_once()


@pytest.mark.asyncio
async def test_post_json__http_error__raises_error(mocker, make_search_service):
    mock_post = mocker.patch("services.search_service.httpx.AsyncClient.post")

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad request",
        request=MagicMock(),
        response=MagicMock(),
    )
    mock_post.return_value = mock_response

    service = make_search_service()
    payload = RegionsRequest(url="http://marketplace.com")

    with pytest.raises(httpx.HTTPStatusError):
        await service.post_json(
            "/regions",
            payload,
            RegionsResponse,
        )


@pytest.mark.asyncio
async def test_get_cache__cached_data__returns_list(make_search_service):
    redis = AsyncMock()
    redis.get.return_value = b'["Kyiv", "Lviv"]'

    service = make_search_service(redis=redis)

    result = await service.get_cache("regions:test")

    assert result == ["Kyiv", "Lviv"]

    redis.get.assert_awaited_once_with("regions:test")


@pytest.mark.asyncio
async def test_get_cache__no_cached_data__returns_none(make_search_service):
    redis = AsyncMock()
    redis.get.return_value = None

    service = make_search_service(redis=redis)

    result = await service.get_cache("regions:test")

    assert result is None

    redis.get.assert_awaited_once_with("regions:test")


@pytest.mark.asyncio
async def test_get_cache__redis_error__returns_none(mocker, make_search_service):
    redis = AsyncMock()
    redis.get.side_effect = RedisError("Redis unavailable")
    mock_logger = mocker.patch("services.search_service.logger")

    service = make_search_service(redis=redis)

    result = await service.get_cache("regions:test")

    assert result is None

    redis.get.assert_awaited_once_with("regions:test")
    mock_logger.warning.assert_called_once_with("Failed to fetch data from cache: %s", redis.get.side_effect)


@pytest.mark.asyncio
async def test_get_cache__invalid_json__returns_none(mocker, make_search_service):
    redis = AsyncMock()
    redis.get.return_value = "{invalid json: 123}"

    mock_logger = mocker.patch("services.search_service.logger")

    service = make_search_service(redis=redis)

    result = await service.get_cache("regions:test")

    assert result is None

    redis.get.assert_awaited_once_with("regions:test")

    assert mock_logger.warning.call_count == 1
    call_args = mock_logger.warning.call_args[0]
    assert call_args[0] == "Failed to fetch data from cache: %s"
    assert isinstance(call_args[1], json.JSONDecodeError)


@pytest.mark.asyncio
async def test_set_cache__valid_data__stores_with_ttl(make_search_service):
    redis = AsyncMock()

    service = make_search_service(redis=redis)

    await service.set_cache(
        "regions:test",
        '["Kyiv", "Lviv"]',
    )

    redis.set.assert_awaited_once_with(
        "regions:test",
        '["Kyiv", "Lviv"]',
        ex=CACHE_TTL,
    )


@pytest.mark.asyncio
async def test_set_cache__redis_error__does_not_raise(mocker, make_search_service):
    redis = AsyncMock()
    redis.set.side_effect = RedisError("Redis unavailable")

    service = make_search_service(redis=redis)
    mock_logger = mocker.patch("services.search_service.logger")

    await service.set_cache(
        "regions:test",
        '["Kyiv"]',
    )

    redis.set.assert_awaited_once()
    mock_logger.warning.assert_called_once_with("Failed to cache data: %s", redis.set.side_effect)


@pytest.mark.asyncio
async def test_get_regions__cache_hit__returns_cached_regions(make_search_service):
    service = make_search_service(redis=MagicMock())
    service.get_cache = AsyncMock(return_value=["Kyiv", "Lviv"])
    service.post_json = AsyncMock()
    service.set_cache = AsyncMock()

    result = await service.get_regions(
        "https://example.com",
    )
    service.get_cache.assert_awaited_once_with("regions:https://example.com")
    assert result == ["Kyiv", "Lviv"]

    service.post_json.assert_not_awaited()
    service.set_cache.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_regions__cache_miss__fetches_regions_and_stores_in_cache(make_search_service):
    service = make_search_service(redis=MagicMock())
    service.get_cache = AsyncMock(return_value=None)
    service.post_json = AsyncMock(return_value=RegionsResponse(regions=["Kyiv", "Lviv"]))
    service.set_cache = AsyncMock()

    result = await service.get_regions(
        "https://example.com",
    )
    service.get_cache.assert_awaited_once_with("regions:https://example.com")
    service.post_json.assert_awaited_once_with(
        "regions",
        RegionsRequest(url="https://example.com"),
        RegionsResponse,
    )
    service.set_cache.assert_awaited_once_with(
        "regions:https://example.com",
        '["Kyiv", "Lviv"]',
    )
    assert result == ["Kyiv", "Lviv"]


@pytest.mark.asyncio
async def test_get_regions__no_regions__returns_empty_list_and_does_not_cache(make_search_service):
    service = make_search_service(redis=MagicMock())
    service.get_cache = AsyncMock(return_value=None)
    service.post_json = AsyncMock(return_value=RegionsResponse(regions=[]))
    service.set_cache = AsyncMock()

    result = await service.get_regions(
        "https://example.com",
    )
    service.get_cache.assert_awaited_once_with("regions:https://example.com")
    service.post_json.assert_awaited_once_with(
        "regions",
        RegionsRequest(url="https://example.com"),
        RegionsResponse,
    )
    service.set_cache.assert_not_awaited()
    assert result == []


@pytest.mark.asyncio
async def test_get_regions__http_error__returns_empty_list_and_does_not_cache(mocker, make_search_service):
    moc_logger = mocker.patch("services.search_service.logger")
    service = make_search_service(redis=MagicMock())
    service.get_cache = AsyncMock(return_value=None)
    service.post_json = AsyncMock(side_effect=httpx.HTTPError("Service unavailable"))
    service.set_cache = AsyncMock()

    result = await service.get_regions(
        "https://example.com",
    )
    service.get_cache.assert_awaited_once_with("regions:https://example.com")
    service.post_json.assert_awaited_once_with(
        "regions",
        RegionsRequest(url="https://example.com"),
        RegionsResponse,
    )
    service.set_cache.assert_not_awaited()
    moc_logger.warning.assert_called_once_with(
        "Failed to fetch regions: %s",
        service.post_json.side_effect,
    )

    assert result == []


@pytest.mark.asyncio
async def test_get_regions__redis_unavailable__fetches_regions(make_search_service):
    service = make_search_service(redis=None)
    service.get_cache = AsyncMock()
    service.post_json = AsyncMock(return_value=RegionsResponse(regions=["Kyiv", "Lviv"]))
    service.set_cache = AsyncMock()

    result = await service.get_regions(
        "https://example.com",
    )
    service.get_cache.assert_not_awaited()
    service.post_json.assert_awaited_once_with(
        "regions",
        RegionsRequest(url="https://example.com"),
        RegionsResponse,
    )
    service.set_cache.assert_not_awaited()
    assert result == ["Kyiv", "Lviv"]


@pytest.mark.asyncio
async def test_get_locations__cache_hit__returns_cached_locations(make_search_service):
    service = make_search_service(redis=MagicMock())
    service.get_cache = AsyncMock(return_value=["loc1", "loc2"])
    service.post_json = AsyncMock()
    service.set_cache = AsyncMock()

    result = await service.get_locations(
        target_url="https://example.com",
        region="Kyiv",
    )
    service.get_cache.assert_awaited_once_with("locations:Kyiv:https://example.com")
    assert result == ["loc1", "loc2"]

    service.post_json.assert_not_awaited()
    service.set_cache.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_locations__cache_miss__fetches_locations_and_stores_in_cache(make_search_service):
    service = make_search_service(redis=MagicMock())
    service.get_cache = AsyncMock(return_value=None)
    service.post_json = AsyncMock(return_value=LocationsResponse(locations=["loc1", "loc2"]))
    service.set_cache = AsyncMock()

    result = await service.get_locations(
        target_url="https://example.com",
        region="Kyiv",
    )
    service.get_cache.assert_awaited_once_with("locations:Kyiv:https://example.com")
    service.post_json.assert_awaited_once_with(
        "locations",
        LocationsRequest(region="Kyiv", url="https://example.com"),
        LocationsResponse,
    )
    service.set_cache.assert_awaited_once_with(
        "locations:Kyiv:https://example.com",
        '["loc1", "loc2"]',
    )
    assert result == ["loc1", "loc2"]


@pytest.mark.asyncio
async def test_get_locations__no_locations__returns_empty_list_and_does_not_cache(make_search_service):
    service = make_search_service(redis=MagicMock())
    service.get_cache = AsyncMock(return_value=None)
    service.post_json = AsyncMock(return_value=LocationsResponse(locations=[]))
    service.set_cache = AsyncMock()

    result = await service.get_locations(
        target_url="https://example.com",
        region="Kyiv",
    )
    service.get_cache.assert_awaited_once_with("locations:Kyiv:https://example.com")
    service.post_json.assert_awaited_once_with(
        "locations",
        LocationsRequest(region="Kyiv", url="https://example.com"),
        LocationsResponse,
    )
    service.set_cache.assert_not_awaited()
    assert result == []


@pytest.mark.asyncio
async def test_get_locations__http_error__returns_empty_list(mocker, make_search_service):
    moc_logger = mocker.patch("services.search_service.logger")
    service = make_search_service(redis=MagicMock())
    service.get_cache = AsyncMock(return_value=None)
    service.post_json = AsyncMock(side_effect=httpx.HTTPError("Service unavailable"))
    service.set_cache = AsyncMock()

    result = await service.get_locations(
        target_url="https://example.com",
        region="Kyiv",
    )

    service.get_cache.assert_awaited_once_with("locations:Kyiv:https://example.com")
    service.post_json.assert_awaited_once_with(
        "locations",
        LocationsRequest(region="Kyiv", url="https://example.com"),
        LocationsResponse,
    )
    service.set_cache.assert_not_awaited()
    moc_logger.warning.assert_called_once_with(
        "Failed to fetch locations: %s",
        service.post_json.side_effect,
    )

    assert result == []


@pytest.mark.asyncio
async def test_get_locations__redis_unavailable__fetches_locations(make_search_service):
    service = make_search_service(redis=None)
    service.get_cache = AsyncMock()
    service.post_json = AsyncMock(return_value=LocationsResponse(locations=["loc1", "loc2"]))
    service.set_cache = AsyncMock()

    result = await service.get_locations(
        target_url="https://example.com",
        region="Kyiv",
    )
    service.get_cache.assert_not_awaited()
    service.post_json.assert_awaited_once_with(
        "locations",
        LocationsRequest(region="Kyiv", url="https://example.com"),
        LocationsResponse,
    )
    service.set_cache.assert_not_awaited()
    assert result == ["loc1", "loc2"]
