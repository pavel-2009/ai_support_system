# Deployment

This document describes the repository's Docker Compose deployment and the corresponding operational checks.

## 1. Requirements

Install:

- Docker Engine 20+.
- Docker Compose v2+ (`docker compose` command).
- At least several GB of free disk space for the PostgreSQL, Grafana and Ollama volumes.
- Network access to pull Docker images and the configured LLM model.

For local development outside Docker, use Python 3.11 or newer.

## 2. Services

Compose starts:

- PostgreSQL 13;
- Redis;
- Alembic migration job;
- FastAPI web service;
- Celery worker;
- Ollama;
- one-shot Ollama model download job;
- frontend/nginx;
- Prometheus;
- Grafana;
- Jaeger.

Default ports:

| Service | Address |
|---|---|
| API | `http://localhost:8001` |
| Frontend | `http://localhost:5173` |
| PostgreSQL | `localhost:5432` |
| Redis | `localhost:6379` |
| Ollama | `http://localhost:11434` |
| Prometheus | `http://localhost:9090` |
| Grafana | `http://localhost:3000` |
| Jaeger | `http://localhost:16686` |

## 3. Environment variables

The application configuration is implemented in `app/app/core/config.py`.

### Application

| Variable | Default |
|---|---|
| `APP_NAME` | `My FastAPI Application` |
| `APP_VERSION` | `1.0.0` |
| `APP_DESCRIPTION` | FastAPI/JWT application description |
| `DOCS_URL` | `/docs` |
| `REDOC_URL` | `/redoc` |
| `OPENAPI_URL` | `/openapi.json` |
| `API_PREFIX` | `/api` |

### Database and authentication

| Variable | Default |
|---|---|
| `DATABASE_URL` | PostgreSQL URL for Compose; SQLite in CI |
| `JWT_SECRET_KEY` | development placeholder — replace outside local development |
| `JWT_ALGORITHM` | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` |

### LLM

| Variable | Default |
|---|---|
| `LLM_BASE_URL` | `http://localhost:11434/v1` in application settings; Compose overrides to `http://ollama:11434/v1` |
| `LLM_API_KEY` | `ollama` |
| `LLM_MODEL` | `llama3.1` |
| `LLM_TIMEOUT` | `20` |
| `LLM_TEMPERATURE` | `0.0` |
| `LLM_AI_CONFIDENCE_THRESHOLD` | `0.8` |
| `LLM_ESCALATION_CONFIDENCE_THRESHOLD` | `0.65` |
| `LLM_TOKEN_LIMIT` | `1024` |
| `LLM_RETRY_ATTEMPTS` | `5` |
| `LLM_RETRY_WAIT_MULTIPLIER` | `1.5` |
| `LLM_RETRY_WAIT_MAX` | `4` |

### Redis / Celery

`REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`.

### Runtime / observability

`LOG_DIR`, `LOG_MAX_BYTES`, `LOG_BACKUP_COUNT`, `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_INSECURE`, `OTEL_ENVIRONMENT`, `MAX_OPERATOR_ACTIVE_CONVERSATIONS`, `CONVERSATION_CACHE_TTL_SECONDS`, `CONVERSATION_CACHE_KEY_PREFIX`.

### Compose/load testing

Compose accepts:

- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`
- `RATE_LIMIT_OVERRIDE`

Locust accepts:

- `LOCUST_USER_PASSWORD`
- `LOCUST_OPERATOR_EMAIL`
- `LOCUST_OPERATOR_PASSWORD`
- `LOCUST_ESCALATION_TIMEOUT`

There is no committed `.env.example` in the repository at the current stage. Create a local `.env` only when overriding settings and never commit secrets.

## 4. Initial setup

Clone the repository and enter it:

```bash
git clone <repository-url>
cd ai_support_system
```

Create optional environment overrides:

```bash
cat > .env <<'EOF'
LLM_MODEL=llama3.1
EOF
```

For a production-like deployment, also set a long random `JWT_SECRET_KEY`.

## 5. Start the stack

Build and start all services:

```bash
docker compose up -d --build
```

Check status:

```bash
docker compose ps
```

Follow application logs:

```bash
docker compose logs -f web
```

Follow worker logs:

```bash
docker compose logs -f celery
```

The first start can take longer because `ollama-model` downloads the configured model.

## 6. Migration lifecycle

The `migrate` service executes:

```bash
alembic upgrade head
```

The API and Celery worker depend on successful completion of this service.

Run migrations manually when operating outside Compose:

```bash
cd app
alembic upgrade head
```

Inspect current revision:

```bash
cd app
alembic current
```

## 7. Healthcheck

Once the stack is running:

```bash
curl http://localhost:8001/health
```

Expected top-level result:

```json
{
  "status": "healthy"
}
```

The exact response also includes individual checks for database, Redis, Celery, LLM API, disk space and open conversations.

If the result is `degraded`, inspect:

```bash
docker compose ps
docker compose logs web
docker compose logs celery
docker compose logs postgres
docker compose logs redis
docker compose logs ollama
```

## 8. Test request

Open Swagger:

```
http://localhost:8001/api/docs
```

Or verify the API directly:

```bash
curl http://localhost:8001/health
```

For an authenticated application request, first register/login through the documented auth endpoints and use the returned bearer token for protected routes.

## 9. Monitoring

### Prometheus

Open:

```
http://localhost:9090
```

The API metrics endpoint is:

```
http://localhost:8001/api/metrics
```

The application itself excludes the metrics endpoint from HTTP request metric instrumentation to avoid recursive metric collection.

### Grafana

Open:

```
http://localhost:3000
```

Compose mounts the repository's Grafana provisioning and dashboards, so the Prometheus datasource/dashboard configuration is loaded from the repository.

### Jaeger

Open:

```
http://localhost:16686
```

OTLP endpoints used by the local Jaeger container are 4317 (gRPC) and 4318 (HTTP).

## 10. Update procedure

For a normal source update:

```bash
git pull
docker compose build
docker compose up -d
```

Because the Compose `migrate` service runs `alembic upgrade head` and `web`/ `celery` depend on its successful completion, schema migrations are applied before those services start after a recreated deployment.

Verify:

```bash
docker compose ps
curl http://localhost:8001/health
```

Then inspect recent logs:

```bash
docker compose logs --tail=200 web
docker compose logs --tail=200 celery
```

For a model change, make sure the configured Ollama model is available and allow `ollama-model` to complete.

## 11. Stop / restart

Stop containers while preserving volumes:

```bash
docker compose down
```

Restart:

```bash
docker compose up -d
```

To remove persistent local data as well:

```bash
docker compose down -v
```

This deletes PostgreSQL, Ollama and Grafana volumes. Do not use `-v` when you need to preserve local data.

## 12. Deployment invariants

- Never deploy with the development JWT secret.
- Apply Alembic migrations before serving application traffic.
- Keep PostgreSQL/Redis credentials out of Git.
- Verify `/health` after deployment.
- Verify Celery worker readiness when AI processing is enabled.
- Check Jaeger/Prometheus/Grafana after observability changes.
- Treat the configured LLM endpoint/model as a runtime dependency of AI functionality.
