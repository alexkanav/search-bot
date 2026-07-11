import json
from unittest.mock import AsyncMock

import pytest
from redis.exceptions import RedisError

from utils.cache import redis_cache


class Service:
    def __init__(self, redis=None):
        self.redis = redis

    @redis_cache(expire=60)
    async def get_data(self, x, y=0):
        return {"result": x + y}


@pytest.mark.asyncio
async def test_redis_cache__redis_is_none__calls_original_function():
    service = Service(redis=None)
    result = await service.get_data(1, y=2)

    assert result == {"result": 3}


@pytest.mark.asyncio
async def test_redis_cache__cache_hit__returns_cached_result():
    redis = AsyncMock()
    redis.get.return_value = json.dumps({"result": 100})
    service = Service(redis)
    result = await service.get_data(1, y=2)

    assert result == {"result": 100}

    redis.get.assert_awaited_once()
    redis.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_redis_cache__cache_miss__calls_function_and_caches_result():
    redis = AsyncMock()
    redis.get.return_value = None
    service = Service(redis)
    result = await service.get_data(2, y=5)

    assert result == {"result": 7}

    redis.get.assert_awaited_once()
    redis.set.assert_awaited_once()
    args, kwargs = redis.set.await_args

    assert json.loads(args[1]) == {"result": 7}
    assert kwargs["ex"] == 60


@pytest.mark.asyncio
async def test_redis_cache__redis_get_raises_error__calls_function_and_caches_result():
    redis = AsyncMock()
    redis.get.side_effect = RedisError()
    service = Service(redis)
    result = await service.get_data(3, y=4)

    assert result == {"result": 7}

    redis.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_redis_cache__redis_set_raises_error__returns_result_without_failing():
    redis = AsyncMock()
    redis.get.return_value = None
    redis.set.side_effect = RedisError()
    service = Service(redis)
    result = await service.get_data(5, y=6)

    assert result == {"result": 11}


class BadService:
    def __init__(self, redis):
        self.redis = redis

    @redis_cache()
    async def get_data(self):
        return object()


@pytest.mark.asyncio
async def test_redis_cache__result_is_not_json_serializable__returns_result_without_caching():
    redis = AsyncMock()
    redis.get.return_value = None
    service = BadService(redis)
    result = await service.get_data()

    assert isinstance(result, object)

    redis.set.assert_not_awaited()
