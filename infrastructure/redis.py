import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


async def get_redis_client(redis_url: str) -> Redis | None:
    client = None

    try:
        client = Redis.from_url(
            redis_url,
            socket_connect_timeout=3,
            socket_timeout=3,
        )

        await client.ping()

        logger.info("Redis connection established")
        return client

    except RedisError:
        logger.warning("Redis unavailable", exc_info=True)

    except Exception:
        logger.exception("Unexpected error during Redis initialization")

    if client is not None:
        await client.aclose()

    return None
