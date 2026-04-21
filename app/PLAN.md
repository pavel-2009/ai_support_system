# PLAN — AI Support System (актуализация на 21 апреля 2026)

## 1) Текущий статус проекта

Проект находится на этапе **расширенного MVP**: базовый продукт стабилен, operator workflow реализован, Celery/LLM интегрированы, CI покрывает unit+e2e тесты и теперь запускает отдельный Celery worker для корректной проверки фоновой инфраструктуры.

Ключевые факты по текущему состоянию:
- CI в `.github/workflows/ci.yml` запускается из корня репозитория с рабочей директорией `app/`.
- В CI поднимаются Redis (service container) и Celery worker (broker/result backend: `redis://localhost:6379/0`), добавлены отдельные проверки готовности Redis и Celery перед запуском тестов.
- `/api/auth/login` поддерживает JSON и OAuth2 form сценарии.
- Реализован полный operator workflow: assign/reply/close/back_to_ai.
- Реализована базовая LLM-интеграция и Celery-задача `process_llm_task`.
- Health endpoint проверяет database/redis/celery.

### Оценка готовности
- **Текущая оценка: ~90%**.
- **Остаток до production-ready: ~10%**.

---

## 2) Что реализовано (Done)

### 2.1 Foundation
- [x] FastAPI приложение и health-check endpoint.
- [x] Слоистая архитектура: `core`, `routers`, `services`, `repositories`, `schemas`, `models`.
- [x] Конфигурация через `pydantic-settings`.
- [x] Централизованное логирование.

### 2.2 Data layer
- [x] ORM модели: users, conversations, messages.
- [x] ORM модели: audit_logs, conversation_operator_links.
- [x] Alembic миграции.
- [x] SQLite (dev/test).

### 2.3 Auth & Access
- [x] JWT access/refresh.
- [x] Роли USER/OPERATOR/ADMIN.
- [x] Разграничение доступа на эндпоинтах.
- [x] Login для API-клиентов и Swagger (JSON + form).

### 2.4 User Conversation API
- [x] Создание диалогов.
- [x] Получение диалога/истории сообщений.
- [x] Отправка сообщений в диалог.
- [x] Закрытие диалога пользователем.
- [x] Списки и очередь активных диалогов для роли operator/admin.

### 2.5 Operator workflow
- [x] Queue endpoint для операторов.
- [x] Assign диалога оператору.
- [x] Reply оператора в диалог.
- [x] Close диалога оператором.
- [x] Возврат диалога в AI (`back_to_ai`).
- [x] История назначений (`ConversationOperatorLink`).

### 2.6 AI / Celery integration
- [x] `LLMService` + `LLMRepository` с retry.
- [x] Celery app и задача `process_llm_task`.
- [x] Подготовка контекста (последние сообщения) для LLM.
- [x] Базовый confidence-based routing в сервисной логике.

### 2.7 CI/CD и тестирование
- [x] CI workflow в корне репозитория.
- [x] Запуск тестов с coverage + junit отчетом.
- [x] Публикация `coverage.xml` и `pytest-report.xml` как артефактов.
- [x] **Добавлен корректный запуск Redis и Celery worker в CI + readiness checks перед тестами.**

---

## 3) Gap до ТЗ (что ещё нужно)

1. **Production DB и окружения**
   - [ ] Переключение на PostgreSQL для production.
   - [ ] Актуализация миграций под production-процессы.
   - [ ] Разделение env-конфигов (dev/test/prod).

2. **Полный AI pipeline (по ТЗ)**
   - [ ] Автотриггер Celery-задачи при `POST /messages`.
   - [ ] Гарантированная запись AI-ответов в `messages` с `is_auto_reply=true`.
   - [ ] Явная обработка диапазонов confidence (`>0.85`, `0.6–0.85`, `<0.6`) с `needs_review`.
   - [ ] Полная эскалация в статус `escalated` + audit событие в одном транзакционном сценарии.

3. **State machine hardening**
   - [ ] Централизованный transition-layer для статусов.
   - [ ] Явная валидация допустимых переходов.
   - [ ] Полный audit trail по сменам статусов.

4. **Observability и эксплуатация**
   - [ ] Prometheus metrics endpoint.
   - [ ] Readiness/liveness в формате production-deploy.
   - [ ] Runbook/операционные инструкции.

5. **Фичи из ТЗ, ещё не закрытые**
   - [ ] Лимит активных диалогов на оператора (до 5).
   - [ ] Auto-close по неактивности (3 часа) через scheduler/cron.
   - [ ] Уведомления операторов (опционально WebSocket/event-driven).

---

## 4) План работ (обновлённый)

### Этап A — Stabilization (завершён)
- [x] Базовая архитектура и основные API.
- [x] Operator workflow.
- [x] CI с корректным запуском Redis/Celery для тестов.

### Этап B — Full AI flow (в работе)
- [ ] Trigger Celery из пользовательского message endpoint.
- [ ] Persist AI message + confidence/needs_review.
- [ ] Эскалация по low confidence в operator queue.

### Этап C — State machine + audit (план)
- [ ] Единый модуль transitions.
- [ ] Строгие правила смены состояний.
- [ ] Полный аудит изменений статусов/назначений.

### Этап D — Production readiness (план)
- [ ] PostgreSQL и production-конфигурация.
- [ ] Метрики и эксплуатационные проверки.
- [ ] Smoke/e2e сценарии полного AI-контура в CI.

---

## 5) Прогноз сроков

- **Осталось: 3–5 рабочих дней** при фокусе на backend.
- Критический путь: Full AI flow → state machine hardening → production infra.

---

## 6) Критерии завершения ближайшего checkpoint

Checkpoint «Full AI flow» считается завершённым, когда:
- [ ] Каждое пользовательское сообщение асинхронно обрабатывается Celery автоматически.
- [ ] AI-ответ и confidence стабильно сохраняются в БД.
- [ ] При `confidence < 0.6` диалог гарантированно эскалируется оператору.
- [ ] Все проверки проходят в CI (включая инфраструктурную проверку Celery worker readiness).
