"""OpenTelemetry configuration and application tracing helpers."""

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Tracer
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

from app.core.config import settings


def get_tracer(scope: str) -> Tracer:
    """Return a tracer for application-owned spans."""
    return trace.get_tracer(scope, settings.APP_VERSION)


def configure_telemetry() -> None:
    """Configure telemetry tracing"""

    resource = Resource.create(
        {
            "service.name": settings.OTEL_SERVICE_NAME,
            "service.version": settings.APP_VERSION,
            "deployment.environment": settings.OTEL_ENVIRONMENT,
        }
    )

    tracer_provider = TracerProvider(resource=resource)

    exporter = OTLPSpanExporter(
        endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        insecure=settings.OTEL_EXPORTER_OTLP_INSECURE
    )

    span_processor = BatchSpanProcessor(exporter)

    tracer_provider.add_span_processor(span_processor)

    HTTPXClientInstrumentor().instrument()
    RedisInstrumentor().instrument()

    trace.set_tracer_provider(tracer_provider)
