"""Redis client creation and dependency provider."""

from redis import Redis
from opentelemetry.instrumentation.redis import RedisInstrumentor

from app.core.config import settings


RedisInstrumentor().instrument()

redis_client = Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)


def get_redis_client() -> Redis:
    """Return the shared Redis client."""
    return redis_client