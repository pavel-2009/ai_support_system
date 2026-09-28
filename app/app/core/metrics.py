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
app_dependency_up = Gauge(
    "app_dependency_up",
    "Whether an application dependency is reachable during the metrics scrape.",
    ("dependency",),
)
celery_tasks_total = Counter(
    "celery_tasks_total",
    "Total number of Celery task executions by task and outcome.",
    ("task_name", "outcome"),
)
celery_task_duration_seconds = Histogram(
    "celery_task_duration_seconds",
    "Celery task execution duration in seconds.",
    ("task_name",),
)
operator_assigned_total = Counter(
    "operators_assigned_total",
    "Total number of operator assignments.",
)
conversation_closed_total = Counter(
    "conversations_closed_total",
    "Total number of closed conversations.",
)
conversation_returned_to_ai_total = Counter(
    "conversations_returned_to_ai_total",
    "Total number of conversations returned to AI.",
)
conversation_review_total = Counter(
    "conversations_marked_for_review_total",
    "Total number of conversations marked for review.",
)
user_registered_total = Counter(
    "users_registered_total",
    "Total number of registered users.",
)
user_updated_total = Counter(
    "users_updated_total",
    "Total number of updated users.",
)
user_deleted_total = Counter(
    "users_deleted_total",
    "Total number of deleted users.",
)


def _request_path(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path)


async def prometheus_middleware(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)

    path = _request_path(request)
    with http_request_duration_seconds.labels(request.method, path).time():
        try:
            response = await call_next(request)
        except Exception:
            http_requests_total.labels(request.method, path, "500").inc()
            raise

    http_requests_total.labels(
        request.method,
        path,
        str(response.status_code),
    ).inc()
    return response


async def refresh_runtime_metrics(session: AsyncSession) -> None:
    """Refresh gauges whose values are derived from external state."""

    try:
        result = await session.execute(
            select(func.count(Conversation.id)).where(Conversation.status != Status.CLOSED)
        )
        active_conversations.set(int(result.scalar_one()))
        app_dependency_up.labels("database").set(1)
    except Exception:
        app_dependency_up.labels("database").set(0)

    redis = None
    try:
        redis = Redis.from_url(settings.CELERY_BROKER_URL)
        celery_queue_length.set(await redis.llen("celery"))
        app_dependency_up.labels("redis").set(1)
    except Exception:
        celery_queue_length.set(0)
        app_dependency_up.labels("redis").set(0)
    finally:
        if redis is not None:
            try:
                await redis.aclose()
            except Exception:
                app_dependency_up.labels("redis").set(0)


async def metrics_response(session: AsyncSession) -> Response:
    await refresh_runtime_metrics(session)
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
