# AI Support System

AI-powered helpdesk backend with asynchronous LLM processing, operator escalation, role-based access, transactional domain logic, background workers, caching/idempotency infrastructure, and production-oriented observability.

The repository contains a FastAPI backend, a small web frontend, PostgreSQL/Redis/Celery infrastructure, an OpenAI-compatible LLM integration, and an observability stack based on Prometheus, Grafana, and Jaeger.

## Key capabilities

- JWT authentication with access and refresh tokens.
- Roles: `user`, `operator`, `admin`.
- Conversation lifecycle management with explicit state transitions.
- User messages persisted in PostgreSQL.
- Asynchronous LLM processing through Celery.
- Confidence-based AI response/review/escalation flow.
- Operator queue, assignment, replies, closing, and return-to-AI workflow.
- Conversation/operator assignment history and audit logs.
- Redis-backed caching and Celery broker/result backend.
- Rate limiting and correlation IDs.
- Domain events with post-commit event publication.
- Prometheus metrics for HTTP, business, Celery and LLM activity.
- OpenTelemetry tracing with Jaeger.
- Health endpoint covering API dependencies and runtime resources.
- Unit and E2E tests plus Locust load testing.
- Docker Compose environment containing the application, databases, workers, LLM, frontend and monitoring stack.

## Architecture at a glance

The backend follows a layered design:

```text
HTTP client
   |
   v
FastAPI routers
   |
   v
Services / business logic
   |
   +----------------------+
   |                      |
   v                      v
Unit of Work          Redis / cache
   |
   +----------------------+
   |          |           |
   v          v           v
Repositories  State       PostgreSQL
              Machine
   |
   v
Domain events -> Event Bus -> handlers

Message requiring AI
   |
   v
Celery task
   |
   +--> short DB read transaction
   |
   +--> LLM request (no DB session held)
   |
   +--> short DB write transaction
```

A detailed architecture is documented in [ARCHITECTURE.md](./ARCHITECTURE.md).

## Technology stack

### Backend

- Python 3.11 runtime in the application Docker image.
- FastAPI 0.135.x.
- Uvicorn.
- Pydantic 2.x / pydantic-settings.
- SQLAlchemy 2.x async.
- Alembic.
- PostgreSQL 13 in Compose.
- Redis 7.x-compatible runtime.
- Celery 5.6.x.
- OpenAI SDK 2.x against an OpenAI-compatible endpoint.
- PyJWT and bcrypt.
- SlowAPI for rate limiting.
- structlog for application logging.
- tenacity and a circuit-breaker integration for transient LLM failures.

### Observability

- Prometheus client.
- Prometheus.
- Grafana.
- OpenTelemetry SDK/exporters/instrumentation.
- Jaeger.

### Testing

- pytest.
- pytest-asyncio.
- pytest-cov.
- httpx.
- Locust.

### Frontend

The repository also contains a Vite-built frontend served by nginx. Docker uses Node 22 for the build stage and nginx 1.27 for the runtime stage.

## Repository layout

```text
.
├── app/
│   ├── app/
│   │   ├── core/                 # configuration and infrastructure
│   │   ├── domain/               # domain events
│   │   ├── models/               # SQLAlchemy models
│   │   ├── repositories/         # persistence and state-machine adapters
│   │   ├── routers/              # HTTP API
│   │   ├── schemas/              # Pydantic schemas
│   │   ├── services/             # business logic
│   │   └── celery/               # Celery application and tasks
│   ├── alembic/                  # database migrations
│   ├── tests/
│   │   ├── unit/
│   │   └── e2e/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── locustfile.py
├── frontend/
├── grafana/
├── docker-compose.yml
├── prometheus.yml
├── ARCHITECTURE.md
├── DEPLOYMENT.md
└── CONTRIBUTING.md
```

## API

The application uses `/api` as the configured FastAPI root path.

### Authentication

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`

### Users

- `GET /api/users/me`
- `PATCH /api/users/me`
- Admin user management endpoints under `/api/users/`.

### Conversations and messages

- `POST /api/conversations/`
- `GET /api/conversations/`
- `GET /api/conversations/{id}`
- `POST /api/conversations/{id}/close`
- `POST /api/conversations/{id}/messages`
- `GET /api/conversations/{id}/messages`

### Operator workflow

- `GET /api/operator/queue`
- `POST /api/operator/assign/{conversation_id}`
- `POST /api/operator/reply/{conversation_id}`
- `POST /api/operator/close/{conversation_id}`
- `POST /api/operator/back_to_ai/{conversation_id}`

### Operations

- `GET /api/health`
- `GET /api/metrics`

Swagger/OpenAPI and ReDoc are available through the configured FastAPI documentation endpoints.

## Conversation lifecycle

Conversation statuses are:

- `open`
- `pending_ai`
- `escalated`
- `waiting_for_operator`
- `waiting_for_user`
- `closed`

The `ConversationStateMachine` owns allowed transitions. Services do not mutate statuses arbitrarily; state changes go through the state-machine abstraction and are audited.

## AI pipeline

1. A user sends a message.
2. The message is persisted and the conversation enters the AI-processing flow.
3. A Celery task loads the required conversation context.
4. The DB session is released before the external LLM request.
5. The LLM response is validated through the application schema.
6. The result is classified by confidence:
   - at or above `LLM_AI_CONFIDENCE_THRESHOLD`: automatic AI response;
   - between the escalation and AI thresholds: AI response marked for review;
   - below the escalation threshold: conversation escalates to an operator.
7. A fresh short DB transaction persists the result.

This split deliberately avoids holding a database connection while waiting for network-bound LLM I/O.

## Docker Compose

The Compose stack contains:

| Service | Purpose | Default port |
|---|---|---:|
| `postgres` | PostgreSQL database | 5432 |
| `redis` | Cache / Celery broker | 6379 |
| `migrate` | Alembic migrations | — |
| `web` | FastAPI application | 8001 |
| `celery` | Background worker | 8002 internally |
| `ollama` | Local OpenAI-compatible LLM API | 11434 |
| `ollama-model` | Pulls configured model once | — |
| `frontend` | Built web UI | 5173 |
| `prometheus` | Metrics collection | 9090 |
| `grafana` | Dashboards | 3000 |
| `jaeger` | Distributed tracing UI/OTLP | 16686 / 4317 / 4318 |

Start the stack:

```bash
docker compose up -d --build
```

The `web` service waits for migrations and the configured Ollama model. PostgreSQL and Ollama have Docker healthchecks; the API also exposes `/health`.

See [DEPLOYMENT.md](./DEPLOYMENT.md) for the complete procedure.

## Local development

The backend can be run without building the complete Compose stack.

```bash
cd app
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run migrations:

```bash
cd app
alembic upgrade head
```

Run the API:

```bash
cd app
PYTHONPATH=. uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

Run a worker:

```bash
cd app
PYTHONPATH=. celery -A app.celery.celery_app:celery_app worker --loglevel=info
```

Local development still requires compatible PostgreSQL/Redis/LLM services unless those dependencies are provided by Docker.

## Configuration

Configuration is defined by `app/app/core/config.py` and loaded through Pydantic Settings. A `.env` file is supported.

Important variables include:

### Application

`APP_NAME`, `APP_VERSION`, `APP_DESCRIPTION`, `DOCS_URL`, `REDOC_URL`, `OPENAPI_URL`, `API_PREFIX`.

### Database

`DATABASE_URL`.

### Authentication

`JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_REFRESH_TOKEN_EXPIRE_DAYS`.

### LLM

`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_TIMEOUT`, `LLM_TEMPERATURE`, `LLM_AI_CONFIDENCE_THRESHOLD`, `LLM_ESCALATION_CONFIDENCE_THRESHOLD`, `LLM_TOKEN_LIMIT`, `LLM_RETRY_ATTEMPTS`, `LLM_RETRY_WAIT_MULTIPLIER`, `LLM_RETRY_WAIT_MAX`.

### Redis / Celery

`REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`.

### Cache / business limits

`CONVERSATION_CACHE_TTL_SECONDS`, `CONVERSATION_CACHE_KEY_PREFIX`, `MAX_OPERATOR_ACTIVE_CONVERSATIONS`.

### Observability

`LOG_DIR`, `LOG_MAX_BYTES`, `LOG_BACKUP_COUNT`, `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_INSECURE`, `OTEL_ENVIRONMENT`.

Compose additionally uses `RATE_LIMIT_OVERRIDE` for load-testing scenarios. Locust supports `LOCUST_USER_PASSWORD`, `LOCUST_OPERATOR_EMAIL`, `LOCUST_OPERATOR_PASSWORD`, and `LOCUST_ESCALATION_TIMEOUT`.

Do not use the default JWT secret outside development. Put secrets in the environment rather than committing them.

## Migrations

Alembic is the source of truth for database schema changes.

```bash
cd app
alembic upgrade head
```

Create a revision after changing SQLAlchemy models:

```bash
cd app
alembic revision --autogenerate -m "describe change"
```

Review generated SQL before applying it. Do not edit an already-applied migration to change production history; create a new revision.

Compose runs `alembic upgrade head` in the dedicated `migrate` service before starting the API and worker.

## Monitoring and tracing

### Health

```bash
curl http://localhost:8001/health
```

The health response checks database, Redis, Celery, LLM API, disk space and the number of open conversations.

### Prometheus

Open `http://localhost:9090`.

The API exposes `/metrics`. The Celery worker exposes a multiprocess Prometheus endpoint on port 8002 inside the Compose network.

Metrics include HTTP request count/duration, active conversations, messages, escalations, operator assignments, conversation closures, return-to-AI operations, LLM latency and Celery task outcomes/durations.

### Grafana

Open `http://localhost:3000`. Compose mounts the repository's provisioning and dashboard configuration.

### Jaeger

Open `http://localhost:16686`. FastAPI and Celery tracing are configured through OpenTelemetry, with OTLP sent to Jaeger.

## Testing

Run the complete test suite:

```bash
cd app
pytest
```

With coverage:

```bash
cd app
pytest --cov=app --cov-report=term-missing
```

The GitHub Actions workflow runs the tests on Python 3.12, uses Redis as a service, starts a Celery worker, and publishes coverage/JUnit artifacts.

### Load testing

Locust is configured in `app/locustfile.py` and exercises registration, login, conversation creation, message sending, escalation, operator assignment and operator replies.

Example:

```bash
cd app
locust -f locustfile.py --host http://localhost:8001 --headless --users 100 --spawn-rate 10 --run-time 5m --csv=tests/performance/results
```

Performance testing is intentionally separate from the normal CI test suite.

## Quality and contribution

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development workflow, migration rules, test commands, static-analysis expectations, branches and pull requests.

## License

See [LICENSE](./LICENSE).
