"""Prometheus metrics used by the application."""

from fastapi import Request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.config import settings
from app.models.conversation import Conversation, Status

http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests.",
    ("method", "path", "status"),
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ("method", "path"),
)
conversations_created_total = Counter(
    "conversations_created_total",
    "Total number of created conversations.",
)
messages_sent_total = Counter(
    "messages_sent_total",
    "Total number of sent messages.",
)
escalations_total = Counter(
    "escalations_total",
    "Total number of conversation escalations.",
)
llm_latency_seconds = Histogram(
    "llm_latency_seconds",
    "LLM request latency in seconds.",
)
active_conversations = Gauge(
    "active_conversations",
    "Current number of non-closed conversations.",
)
celery_queue_length = Gauge(
    "celery_queue_length",
    "Current number of tasks waiting in the default Celery queue.",
)


def _request_path(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path)


async def prometheus_middleware(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)

    path = _request_path(request)
    with http_request_duration_seconds.labels(request.method, path).time():
        response = await call_next(request)

    http_requests_total.labels(
        request.method,
        path,
        str(response.status_code),
    ).inc()
    return response


async def refresh_runtime_metrics(session: AsyncSession) -> None:
    """Refresh gauges whose values are derived from external state."""

    result = await session.execute(
        select(func.count(Conversation.id)).where(Conversation.status != Status.CLOSED)
    )
    active_conversations.set(int(result.scalar_one()))

    redis = Redis.from_url(settings.CELERY_BROKER_URL)
    try:
        celery_queue_length.set(await redis.llen("celery"))
    finally:
        await redis.aclose()


async def metrics_response(session: AsyncSession) -> Response:
    await refresh_runtime_metrics(session)
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
