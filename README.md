# AI Support System

Бэкенд-система поддержки пользователей с AI-ассистентом и операторской очередью (аналог helpdesk-платформ).

Проект построен вокруг **FastAPI + SQLAlchemy 2.x (async) + PostgreSQL + Redis + Celery + LLM**, с JWT-аутентификацией, ролями пользователей, операторским workflow, кэшированием, идемпотентностью, rate limiting и observability через Prometheus, Grafana и Jaeger.

---

## Что умеет система

- Регистрация и вход пользователей (JWT access/refresh).
- Ролевая модель: `user`, `operator`, `admin`.
- Создание и ведение диалогов (`conversations`) между пользователем, AI и оператором.
- Отправка сообщений и хранение истории диалога.
- Фоновая LLM-обработка через Celery-задачи.
- Эскалация диалога оператору при низкой уверенности AI.
- Операторская очередь: взять диалог, ответить, закрыть, вернуть в AI.
- Health-check и метрики Prometheus.

---

## Архитектура и стек

### Технологии

- **Python 3.10+**
- **FastAPI** (REST API)
- **SQLAlchemy 2.x (async)** + **Alembic** (миграции)
- **PostgreSQL** (основная БД)
- **Redis** (broker/backend для Celery)
- **Celery** (фоновые задачи)
- **OpenAI SDK / OpenRouter** (LLM интеграция)
- **PyJWT + bcrypt** (аутентификация)
- **pytest + pytest-cov** (тестирование)

### Слои приложения

```text
app/
├─ main.py                    # FastAPI entrypoint, middleware, health/metrics
├─ app/
│  ├─ core/                   # infrastructure: config, security, cache, UoW,
│  │                          # events, idempotency, rate limit, logging,
│  │                          # metrics, correlation, telemetry, WebSocket
│  ├─ domain/                 # domain events
│  ├─ models/                 # SQLAlchemy models
│  ├─ schemas/                # Pydantic API schemas
│  ├─ repositories/           # persistence + LLM adapter
│  ├─ services/               # business logic
│  ├─ routers/                # user and operator HTTP API
│  └─ celery/tasks/           # background LLM processing
├─ alembic/                   # PostgreSQL migrations
├─ tests/
│  ├─ unit/
│  ├─ e2e/
│  └─ performance/
├─ locustfile.py              # load testing
└─ prometheus.yml             # Prometheus config

frontend/
├─ src/
│  ├─ components/             # user/operator/admin UI
│  ├─ hooks/                  # auth and operator WebSocket hooks
│  └─ api/                    # API client
├─ Dockerfile
└─ vite.config.js

grafana/
├─ dashboards/
└─ provisioning/
```

---

## Доменные сущности

### Пользователи

- `User`: nickname, fullname, email, hashed_password, role, active_conversations_count.
- Роли: `user`, `operator`, `admin`.

### Диалоги

- `Conversation`: user_id, operator_id, status, priority, channel, ai_confidence, timestamps.
- Статусы: `open`, `waiting_for_user`, `waiting_for_operator`, `escalated`, `pending_ai`, `closed`.

### Сообщения

- `Message`: sender_type (`user`/`ai`/`operator`), sender_id, content, confidence, needs_review.

### Аудит и история назначений

- `AuditLog` — фиксация действий по диалогу.
- `ConversationOperatorLink` — история назначений операторов.

---

## API (основные группы)

> Префикс OpenAPI задаётся `root_path` и по умолчанию равен `/api`.

### Auth

- `POST /auth/register` — регистрация.
- `POST /auth/login` — вход (JSON и form-data для Swagger).
- `POST /auth/refresh` — обновление токена.

### Users

- `GET /users/me` — текущий пользователь.
- `GET /users/` — список пользователей (admin).
- `GET /users/{id}` / `PATCH /users/{id}` / `DELETE /users/{id}`.
- `PATCH /users/me`.

### Conversations

- `POST /conversations/` — создать диалог.
- `GET /conversations/` — список с фильтрацией и пагинацией.
- `GET /conversations/{id}` — получить диалог.
- `POST /conversations/{id}/close` — закрыть.
- `GET /conversations/queue/active` — активная очередь (admin).

### Messages

- `POST /conversations/{id}/messages` — отправить сообщение.
- `GET /conversations/{id}/messages` — получить историю.

### Operator

- `GET /operator/queue` — очередь оператора.
- `POST /operator/assign/{conversation_id}` — взять в работу.
- `POST /operator/reply/{conversation_id}` — ответить.
- `POST /operator/close/{conversation_id}` — закрыть.
- `POST /operator/back_to_ai/{conversation_id}` — вернуть в AI.

### Service endpoints

- `GET /health` — состояние API/DB/Redis/Celery.
- `GET /metrics` — Prometheus metrics.

---

## Как работает AI-пайплайн

1. Пользователь отправляет сообщение в диалог.
2. Сообщение сохраняется, затем ставится Celery-задача `process_llm_task`.
3. Задача формирует запрос, отправляет его в LLM и получает ответ.
4. Ответ проходит проверку структуры, JSON-декодирование и строгую Pydantic-валидацию.
5. Развилка по `confidence`:
   - `>= LLM_AI_CONFIDENCE_THRESHOLD` — AI отвечает автоматически;
   - `>= LLM_ESCALATION_CONFIDENCE_THRESHOLD` — AI отвечает, но с `needs_review=True`;
   - ниже порога — диалог переводится в `escalated`.

LLM-запрос выполняется **один раз**. Ошибка запроса, некорректный JSON или ошибка валидации не запускают автоматические повторы.

---

## Проблема с PostgreSQL под нагрузкой

Во время нагрузочного тестирования на 100 пользователей с `10 users/s` в течение 5 минут обнаружился bottleneck вокруг DB connection pool и lifecycle SQLAlchemy session в Celery.

Наблюдались рост P95/P99 latency и большое количество HTTP 500 при отправке сообщений. 500 также появлялись на части операций получения и создания диалогов. При этом отдельные обычные SQL-запросы выполнялись значительно быстрее полного request pipeline.

### Причина

Старая схема Celery держала Unit of Work во время ожидания LLM:

```text
open UnitOfWork
      │
      ├─ DB query: история диалога
      │
      ├─ await LLM request  ← долгое сетевое ожидание
      │
      └─ DB write
close UnitOfWork
```

То есть lifecycle DB session/transaction охватывал не только работу с БД, но и внешний LLM I/O. При большом количестве параллельных задач это увеличивало время удержания DB resources. При исчерпании pool новые операции могли ждать до `pool_timeout`, а затем получать ошибку SQLAlchemy.

**Важно:** увеличение pool само по себе проблему не исправляет — оно только увеличивает запас по числу соединений.

### Как решаем

Celery pipeline разделён на две короткие DB-фазы:

```text
Phase 1
┌─────────────────────────────┐
│ DB session                  │
│ - проверить conversation    │
│ - получить history/prompt   │
└──────────────┬──────────────┘
               │ session closed
               ▼
        ┌───────────────┐
        │ LLM request   │
        │ без DB session│
        └───────┬───────┘
                │ response
                ▼
Phase 2
┌─────────────────────────────┐
│ новая DB session            │
│ - сохранить AI message      │
│ - изменить status/escalate  │
└─────────────────────────────┘
```

Дополнительно pool увеличен:

```text
pool_size:    20 → 30
max_overflow: 10 → 20
pool_timeout: 30s
pool_pre_ping: enabled
pool_recycle: 3600s
```

Основной фикс — **не удерживать DB transaction во время LLM I/O**.

Текущий фикс намеренно минимальный. В Celery-задаче пока создаётся отдельный SQLAlchemy engine/pool на выполнение task и затем освобождается. Следующим отдельным этапом нужно оптимизировать lifecycle engine/pool на уровне Celery worker и отдельно настроить LLM/Celery concurrency.

---
## Конфигурация и переменные окружения

Основные переменные (из `Settings`):

### Application

- `APP_NAME`
- `APP_VERSION`
- `APP_DESCRIPTION`
- `DOCS_URL`
- `REDOC_URL`
- `OPENAPI_URL`
- `API_PREFIX`

### Database

- `DATABASE_URL`

> В CI по умолчанию используется SQLite (`sqlite+aiosqlite:///./app.db`), локально/в docker-compose — PostgreSQL.

### JWT

- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS`

### LLM

- `LLM_BASE_URL` (по умолчанию `http://localhost:11434/v1`, OpenAI-совместимый endpoint Ollama)
- `LLM_API_KEY`
- `LLM_MODEL`
- `LLM_TIMEOUT`
- `LLM_TEMPERATURE`
- `LLM_AI_CONFIDENCE_THRESHOLD`
- `LLM_ESCALATION_CONFIDENCE_THRESHOLD`
- `LLM_TOKEN_LIMIT`

По умолчанию приложение использует локальную модель Ollama `llama3.1`. Перед запуском установите Ollama и выполните `ollama pull llama3.1`. Для OpenRouter задайте в `.env` `LLM_BASE_URL=https://openrouter.ai/api/v1`, `LLM_API_KEY` и нужную `LLM_MODEL`.

### Celery / Redis

- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`

### Business

- `MAX_OPERATOR_ACTIVE_CONVERSATIONS`

---

## Запуск проекта

## 1) Через Docker Compose (рекомендуется)

Из корня репозитория:

```bash
docker compose up --build
```

Поднимутся сервисы:

- `web` (FastAPI + alembic upgrade)
- `postgres`
- `redis`
- `celery`
- `ollama` (локальный OpenAI-совместимый LLM API)
- `ollama-model` (однократно скачивает модель из `LLM_MODEL`)

API по умолчанию: `http://localhost:8001/api/docs`.

Веб-интерфейс доступен по адресу `http://localhost:5173`. Он автоматически
подбирает рабочее пространство по роли текущего пользователя: клиентский чат,
очередь и WebSocket-уведомления для операторов, а также дашборд метрик для
администраторов. Frontend проксирует API через `/api`, поэтому отдельная
настройка CORS в браузере не требуется.

Grafana доступна по адресу `http://localhost:3000`; datasource Prometheus и
дашборд `AI Support Overview` загружаются автоматически. Prometheus доступен
по адресу `http://localhost:9090` и собирает метрики API и Celery worker.

По умолчанию Compose использует `http://ollama:11434/v1` и модель `llama3.1`. Модели сохраняются в volume `ollama_data`; при первом запуске потребуется скачать несколько гигабайт.

## 2) Локально (без Docker)

```bash
cd app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Запуск API:

```bash
PYTHONPATH=. uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

Запуск Celery worker:

```bash
PYTHONPATH=. celery -A app.celery.celery_app:celery_app worker --loglevel=info
```

Миграции:

```bash
cd app
alembic upgrade head
```

---

## Тестирование и покрытие

Запуск всех тестов с покрытием:

```bash
cd app
pytest --cov=app --cov-report=term-missing
```

## Нагрузочное тестирование

Для нагрузочных тестов используется Locust (`app/locustfile.py`). Например:

```bash
RATE_LIMIT_OVERRIDE=10000/minute docker compose up -d --build
locust -f locustfile.py \
  --host http://localhost:8001 \
  --headless \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --csv=tests/performance/results
```

Результаты сохраняются в `app/tests/performance/`.

---

## Наблюдаемость

- HTTP-метрики через middleware (`http_requests_total`, `http_request_duration_seconds`), включая 5xx.
- Бизнес-метрики: диалоги, сообщения, эскалации, назначения операторов и операции пользователей.
- Runtime-метрики: активные диалоги, Celery queue depth и доступность БД/Redis.
- Celery task outcomes/duration и LLM latency скрейпятся с отдельного worker exporter.
- `/metrics` и внутренний Celery exporter на порту `8002` для Prometheus scraping.
- `/health` с проверками API/DB/Redis/Celery.
- Централизованное логирование через `app.core.logging`.
- Jaeger UI: `http://localhost:16686`.

---

## Ограничения и roadmap

Текущая версия — robust MVP backend. Для production-уровня обычно добавляют:

- stricter валидацию и унификацию error-моделей;
- rate limiting / anti-abuse;
- идемпотентность для message ingestion;
- расширенную observability (tracing, structured audit analytics);
- websocket-уведомления операторов;
- полноценные SLA/SLO и policy-автоматизацию.

---

## Лицензия

См. файл [LICENSE](./LICENSE).
