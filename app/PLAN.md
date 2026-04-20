# PLAN — AI Support System (актуализация на 20 апреля 2025)

## 1) Текущий статус проекта

Проект находится на этапе **стабильного MVP с реализованным operator workflow и базовой AI-интеграцией**.

Ключевые обновления текущего состояния:
- CI вынесен в корневой `.github/workflows/ci.yml`, workflow запускается корректно.
- CI адаптирован под фактическую структуру репозитория (рабочая директория `app/`, корректные пути к артефактам).
- `/api/auth/login` поддерживает и JSON-логин (email/password), и OAuth2 form-login (username/password) для Swagger.
- Реализован полный operator workflow: assign/reply/close/back_to_ai.
- Интегрирована Celery для фоновой обработки LLM-запросов.
- Реализован LLM adapter с OpenAI и retry-логикой.
- Все тесты проходят: **86/86 passed**.

### Процент готовности

- **Оценка выполненной работы: ~90%**.
- **Оставшийся объём: ~10%**.

---

## 2) Что уже сделано (Done)

### 2.1 Foundation
- [x] Базовый FastAPI app + health-check.
- [x] Разделение на слои `core`, `routers`, `services`, `repositories`, `schemas`, `models`.
- [x] Централизованное логирование.
- [x] Конфигурация через pydantic-settings (.env support).

### 2.2 Данные
- [x] Модели: `users`, `conversations`, `messages`.
- [x] Модели: `audit_logs`, `conversation_operator_links`.
- [x] Alembic миграции настроены.
- [x] SQLite (aiosqlite) для разработки/тестирования.

### 2.3 Auth и доступ
- [x] JWT access/refresh tokens.
- [x] Ролевая модель: USER, OPERATOR, ADMIN.
- [x] Ролевая изоляция на всех эндпоинтах.
- [x] Совместимый логин для API-клиентов и Swagger (JSON + OAuth2 form).
- [x] Dependency injection для сервисов и репозиториев.

### 2.4 Conversation API (user)
- [x] `POST /api/conversations/` — создать диалог.
- [x] `GET /api/conversations/{id}` — получить диалог (с `410` для closed).
- [x] `GET /api/conversations/{id}/messages` — получить сообщения.
- [x] `POST /api/conversations/{id}/messages` — отправить сообщение.
- [x] `GET /api/conversations/queue/active` — активная очередь (admin/operator).
- [x] `GET /api/conversations` — список с фильтрами + пагинация.
- [x] `POST /api/conversations/{id}/close` — закрыть диалог (user).
- [x] Проверки изоляции: пользователь видит только свои диалоги.

### 2.5 Operator workflow (полный)
- [x] `GET /api/operator/queue` — список диалогов в очереди.
- [x] `POST /api/operator/assign/{conversation_id}` — назначить диалог оператору.
- [x] `POST /api/operator/reply/{conversation_id}` — ответить в диалоге.
- [x] `POST /api/operator/close/{conversation_id}` — закрыть диалог.
- [x] `POST /api/operator/back_to_ai/{conversation_id}` — вернуть диалог в очередь ИИ.
- [x] Проверка ролей: только OPERATOR/ADMIN.
- [x] История назначений через `ConversationOperatorLink`.

### 2.6 AI integration
- [x] LLMService + LLMRepository с OpenAI client.
- [x] Схема валидации LLMResponse (answer, confidence, topic).
- [x] Retry-логика при ошибках LLM.
- [x] Celery задача `process_llm_task` для фоновой обработки.
- [x] Генерация промптов с историей сообщений (последние 5).
- [x] Confidence-based routing (настроено в config).

### 2.7 CI/CD и качество
- [x] CI workflow в корне репозитория.
- [x] Сбор артефактов `coverage.xml` и `pytest-report.xml`.
- [x] Покрытие тестами: unit + e2e.
- [x] Все тесты зелёные (`86 passed`).

### 2.8 Health & Observability
- [x] `/health` endpoint с проверкой database, redis, celery.
- [x] AuditLog модель для трекинга действий.
- [x] Структурированное логирование.

---

## 3) Что не реализовано (Gap к production-ready)

1. **Production DB**
   - Нет PostgreSQL (сейчас SQLite для dev/test).
   - Нет миграций на production.

2. **AI processing (production-hardened)**
   - Нет полного orchestration-пайплайна после сообщения пользователя.
   - Нет автоматического триггера LLM-задачи при новом сообщении.
   - Нет confidence-routing в production-потоке (интеграция pending).

3. **Observability / эксплуатация**
   - Нет метрик Prometheus endpoint.
   - Нет readiness/liveness probe для K8s.
   - Нет дашбордов/алертинга.
   - Нет WebSocket уведомлений для операторов.

4. **Дополнительные функции**
   - Нет лимита активных диалогов на оператора.
   - Нет cron-задач для авто-закрытия неактивных диалогов.
   - Нет экспорта диалогов (JSON/CSV).
   - Нет системы шаблонов ответов.

---

## 4) Обновлённый план до production-ready

## Этап A —已完成 (Conversation API + Operator workflow)
- [x] Полный CRUD для conversations/messages.
- [x] Operator workflow: assign/reply/close/back_to_ai.
- [x] Ролевая изоляция и проверки прав.

## Этап B — AI pipeline integration (1–2 дня)
- [ ] Автоматический триггер Celery-задачи при POST /messages.
- [ ] Сохранение AI-ответа в messages (is_auto_reply=true).
- [ ] Обновление статуса диалога на основе confidence.
- [ ] Эскалация при low confidence (< threshold).

## Этап C — State machine hardening (1 день)
- [ ] Централизовать переходы статусов (единый transition слой).
- [ ] Явно валидировать допустимые переходы.
- [ ] Audit log при каждом переходе статуса.

## Этап D — Production DB & deployment (1–2 дня)
- [ ] Docker-compose с PostgreSQL + Redis.
- [ ] Миграции Alembic для production.
- [ ] Environment-specific конфиги (.env.prod).

## Этап E — Observability + polishing (1–2 дня)
- [ ] Prometheus metrics endpoint.
- [ ] Health check readiness/liveness.
- [ ] Runbook/README polishing.
- [ ] Базовые smoke/e2e проверки full AI-flow в CI.

---

## 5) Остаточная оценка сроков

- **Осталось: 3–5 рабочих дней**.
- **Оптимистично:** 3 дня.
- **Реалистично:** 4–5 дней.

---

## 6) Критерий завершения текущего checkpoint

Checkpoint «operator workflow + AI integration» считается завершённым:
- [x] CI расположен и работает из корня репозитория.
- [x] Локально проект проходит тесты (86 passed).
- [x] Логин совместим с текущими тестами и Swagger.
- [x] Operator workflow полностью реализован (assign/reply/close/back_to_ai).
- [x] LLM service + repository интегрированы с OpenAI.
- [x] Celery настроен для фоновых задач.

**Checkpoint status: завершён, следующий фокус — AI pipeline automation + state machine hardening + production deployment.**

---

## 7) Архитектурные заметки

### Слои приложения
```
app/
├── main.py              # Точка входа, регистрация роутеров
├── db.py                # SQLAlchemy engine, session factory
├── services_init.py     # Глобальная инициализация сервисов
├── core/
│   ├── config.py        # Pydantic settings
│   ├── security.py      # JWT, password hashing
│   ├── dependencies.py  # FastAPI Depends
│   ├── logging.py       # Конфигурация логов
│   └── exceptions.py    # Кастомные исключения
├── models/              # SQLAlchemy ORM модели
├── schemas/             # Pydantic схемы
├── repositories/        # Data access layer
├── services/            # Business logic layer
├── routers/
│   ├── users/           # User auth, conversations, messages
│   └── operator/        # Operator workflow
├── celery/
│   ├── celery_app.py    # Celery конфигурация
│   └── tasks/
│       └── llm_tasks.py # LLM фоновые задачи
└── tests/
    ├── unit/            # Unit тесты
    └── e2e/             # End-to-end тесты
```

### Статусы диалогов (State Machine)
```
open → waiting_for_user → open (цикл)
open → escalated (при low confidence AI)
escalated → waiting_for_operator (assign)
waiting_for_operator → waiting_for_user (reply)
waiting_for_user → closed (timeout или user close)
any → back_to_ai (operator decision)
```

### Ключевые конфигурации
- `LLM_AI_CONFIDENCE_THRESHOLD`: 0.8 (порог для auto-answer)
- `LLM_RETRY_ATTEMPTS`: 5
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: 30
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS`: 7
