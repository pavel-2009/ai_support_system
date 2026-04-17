# PLAN — AI Support System (актуализация на 17 апреля 2026)

## 1) Текущий статус проекта

Проект находится на этапе **user/auth + conversations + messages + базовый operator queue/audit + unit-покрытие LLM-слоя**:

- Реализована FastAPI-архитектура по слоям (`routers/services/repositories/models/schemas`).
- Реализованы `users`, `conversations`, `messages` (модели, репозитории, сервисы, роутеры).
- Реализованы auth-flow: `register`, `login`, `refresh`, `logout`.
- Добавлены базовые `audit_logs` (события создания/смены статуса/назначения/закрытия).
- Добавлена промежуточная модель `conversation_operator_links` (история назначений операторов).
- Добавлен endpoint очереди активных диалогов с сортировкой по приоритету: `GET /api/conversations/queue/active`.
- Добавлены unit-тесты для `LLMService` и `LLMRepository` (happy/error/retry/fallback branch coverage).

### Процент готовности

- **Оценка выполненной работы: ~65%**.
- **Оставшийся объём: ~35%**.

> Почему 65%: закрыт пользовательский контур + базовые аудит/очередь и тестовый фундамент LLM-слоя, но ещё не реализованы production-ready AI pipeline, полный операторский workflow, ограничения нагрузки и observability-метрики.

---

## 2) Что уже сделано (Done)

### 2.1 Foundation
- [x] Базовый FastAPI app + роутеры + health-check.
- [x] Разделение на слои `core`, `routers`, `services`, `repositories`, `schemas`, `models`.
- [x] Базовая конфигурация через settings.

### 2.2 Данные
- [x] Модель `users` + миграции.
- [x] Модель `conversations`.
- [x] Модель `messages`.
- [x] Модель `audit_logs` + миграция.
- [x] Модель `conversation_operator_links` + миграция.

### 2.3 Auth и доступ
- [x] Регистрация.
- [x] JWT access/refresh.
- [x] Логин + refresh endpoint.
- [x] RBAC для admin/user.
- [~] Частично: operator-сценарии реализованы только для просмотра active queue.

### 2.4 API поддержки
- [x] `POST /api/conversations/`.
- [x] `GET /api/conversations/{id}`.
- [x] `GET /api/conversations/{id}/messages`.
- [x] `POST /api/conversations/{id}/messages`.
- [x] `GET /api/conversations/queue/active` (operator/admin).
- [ ] Список диалогов пользователя.
- [ ] `POST /conversations/{id}/close` для пользователя.
- [ ] Полноценный transition API для операторов.

### 2.5 Качество
- [x] Unit/e2e тесты для user/auth.
- [x] Unit/e2e тесты для users/conversations/messages.
- [x] Unit-тесты для audit/operator-links/active-queue.
- [x] Unit-тесты для LLM service/repository (парсинг, fallback, retry, ошибки).

---

## 3) Что не реализовано (Gap к MVP)

1. **AI processing (production-ready)**
   - Нет фонового async pipeline с worker orchestration.
   - Нет confidence routing и fallback-эскалации на уровне бизнес-процесса.
   - Нет полноценной интеграции LLM-ответов в message-flow API.

2. **Operator workflow (полный)**
   - Нет API: `assign/reply/close/back_to_ai`.
   - Нет лимита активных диалогов на оператора.
   - Нет правил SLA/таймаутного автозакрытия.

3. **User conversation completeness**
   - Нет списка собственных диалогов с фильтрами/пагинацией.
   - Нет user-эндпоинта закрытия диалога.

4. **Observability / эксплуатация**
   - Нет метрик Prometheus.
   - Нет readiness endpoint.
   - Нет структурированных AI-событий (latency/confidence/escalation).

---

## 4) Обновлённый план до MVP

## Этап A — Conversation API completion (1–2 дня)
- `GET /conversations` (фильтры, пагинация).
- `POST /conversations/{id}/close` (user).
- Доработка проверок изоляции и прав.

## Этап B — Operator workflow completion (2–3 дня)
- `POST /operator/assign/{conversation_id}`.
- `POST /operator/reply/{conversation_id}`.
- `POST /operator/close/{conversation_id}`.
- `POST /operator/back_to_ai/{conversation_id}`.
- Ограничение до N активных диалогов на оператора.

## Этап C — State machine hardening (1–2 дня)
- Валидация допустимых переходов статусов.
- Централизация transition-логики.
- Расширение audit-полей при переходах.

## Этап D — AI adapter и routing (2–3 дня)
- Интерфейс LLM adapter + OpenAI реализация.
- Асинхронный pipeline для AI-взаимодействий.
- Confidence routing и fallback-эскалация.

## Этап E — Observability + polishing (1–2 дня)
- JSON-логи и метрики.
- Health + readiness.
- Обновление README/runbook.

---

## 5) Остаточная оценка сроков

- **Осталось: 5–8 рабочих дней**.
- **Оптимистично:** 5–6 дней.
- **Реалистично:** 7–8 дней.

---

## 6) Критерий завершения текущего этапа (checkpoint)

Текущий этап (**user/auth + conversations + messages + basic audit/queue + LLM unit coverage**) считается завершённым, когда:
- message-поток стабилен (create/list) для авторизованных участников диалога;
- базовые audit-события и история назначений операторов сохраняются;
- active queue доступна operator/admin и сортируется по priority;
- LLM service/repository покрыты unit-тестами по ключевым веткам;
- зафиксирован backlog на `state machine hardening/AI/full operator workflow`.

**Checkpoint status: почти достигнут; следующий фокус — completion operator workflow + state machine hardening + AI pipeline integration.**
