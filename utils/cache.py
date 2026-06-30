import functools
import hashlib
import json
from collections.abc import Awaitable, Callable
from typing import Any

from redis.asyncio import Redis, RedisError


def redis_cache(expire: int = 300) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            redis: Redis | None = getattr(self, "redis", None)

            if redis is None:
                return await func(self, *args, **kwargs)

            payload = json.dumps(
                {
                    "args": args,
                    "kwargs": kwargs,
                },
                sort_keys=True,
                default=str,
            )

            key = (
                f"{func.__module__}:"
                f"{func.__qualname__}:"
                f"{hashlib.sha256(payload.encode()).hexdigest()}"
            )

            try:
                cached = await redis.get(key)
            except RedisError:
                cached = None

            if cached is not None:
                return json.loads(cached)

            result = await func(self, *args, **kwargs)

            try:
                await redis.set(key, json.dumps(result), ex=expire)
            except (RedisError, TypeError):
                pass
            return result

        return wrapper

    return decorator
