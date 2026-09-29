"""Redis client creation and dependency provider."""

from redis.asyncio import Redis

from app.core.config import settings


def create_redis_client() -> Redis:
    """Create a Redis client owned by the caller."""
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)


redis_client = create_redis_client()


def get_redis_client() -> Redis:
    """Return the shared Redis client."""
    return redis_client