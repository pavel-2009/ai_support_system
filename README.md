# AI Support System

Бэкенд-система поддержки пользователей с AI-ассистентом и операторской очередью (аналог helpdesk-платформ).

Проект реализован на **FastAPI + SQLAlchemy (async) + Celery + Redis + PostgreSQL**, с JWT-аутентификацией, ролями пользователей и асинхронной обработкой сообщений через LLM.

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
├─ main.py                    # Точка входа FastAPI, middleware, health/metrics
├─ app/
│  ├─ core/                   # Конфиг, безопасность, зависимости, логирование
│  ├─ models/                 # SQLAlchemy-модели
│  ├─ schemas/                # Pydantic-схемы API
│  ├─ repositories/           # Доступ к данным и LLM client adapter
│  ├─ services/               # Бизнес-логика
│  ├─ routers/                # HTTP-роутеры (users, conversations, operator)
│  └─ celery/tasks/           # Фоновые LLM-задачи
├─ alembic/                   # Миграции БД
└─ tests/                     # Unit + E2E тесты
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
3. Задача запрашивает LLM-ответ и confidence.
4. Развилка по confidence:
   - `>= LLM_AI_CONFIDENCE_THRESHOLD` — AI отвечает автоматически;
   - `>= LLM_ESCALATION_CONFIDENCE_THRESHOLD` — AI отвечает, но с `needs_review=True`;
   - ниже порога — диалог переводится в `escalated`.

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

- `LLM_API_KEY`
- `LLM_MODEL`
- `LLM_RETRY_ATTEMPTS`
- `LLM_TIMEOUT`
- `LLM_TEMPERATURE`
- `LLM_AI_CONFIDENCE_THRESHOLD`
- `LLM_ESCALATION_CONFIDENCE_THRESHOLD`
- `LLM_TOKEN_LIMIT`

### Celery / Redis

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

API по умолчанию: `http://localhost:8001/api/docs`.

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

Актуальный результат в рабочем окружении: **110 passed, 90% total coverage**.

> Примечание: в тестах есть 2 warning, связанные с моками coroutine в LLM task-тестах; на статус прохождения это не влияет.

---

## Наблюдаемость

- HTTP-метрики через middleware (`http_requests_total`, `http_request_duration_seconds`).
- `/metrics` для Prometheus scraping.
- `/health` с проверками API/DB/Redis/Celery.
- Централизованное логирование через `app.core.logging`.

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
