# PLAN — AI Support System (актуализация на 16 апреля 2026)

## 1) Текущий статус проекта

Проект перешёл на этап **user/auth + conversations + базовый messages контур**:

- Реализована FastAPI-архитектура по слоям (`routers/services/repositories/models/schemas`).
- Реализованы `users`, `conversations`, `messages` (модели, репозитории, сервисы, роутеры).
- Реализованы auth-flow: `register`, `login`, `refresh`, `logout`.
- Реализованы RBAC-проверки для user/admin и ограничения доступа к чужим диалогам/сообщениям.
- Тестовый набор расширен: покрыты схемы, сервисы, репозитории, роутеры и edge cases для сообщений.

### Процент готовности

- **Оценка выполненной работы: ~50%**.
- **Оставшийся объём: ~50%**.

> Почему 50%: закрыт базовый пользовательский контур сообщений (создание/чтение), но ещё отсутствуют аудит действий, state machine переходов, AI-routing и операторская очередь.

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
- [ ] `audit_logs` — не реализованы.

### 2.3 Auth и доступ
- [x] Регистрация.
- [x] JWT access/refresh.
- [x] Логин + refresh endpoint.
- [x] RBAC для admin/user.
- [~] Частично: operator-сценарии и расширенный workflow доступа не завершены.

### 2.4 API поддержки
- [x] `POST /api/conversations/`.
- [x] `GET /api/conversations/{id}`.
- [x] `GET /api/conversations/{id}/messages`.
- [x] `POST /api/conversations/{id}/messages`.
- [ ] Список диалогов пользователя.
- [ ] Close/reopen/status transition API.

### 2.5 Качество
- [x] Unit/e2e тесты для user/auth.
- [x] Unit/e2e тесты для users/conversations.
- [x] Unit-тесты для message-схем, репозитория, сервиса и роутера (включая edge cases).

---

## 3) Что не реализовано (Gap к MVP)

1. **Домен поддержки**
   - Нет `audit_logs` и протоколирования действий.

2. **AI processing**
   - Нет LLM adapter/pipeline обработки.
   - Нет confidence routing и fallback-эскалации.

3. **Operator workflow**
   - Нет очереди эскалаций.
   - Нет `assign/reply/close/back_to_ai` API для операторов.
   - Нет лимита активных диалогов на оператора.

4. **Observability / эксплуатация**
   - Нет audit trail и метрик Prometheus.
   - Нет readiness endpoint.

---

## 4) Обновлённый план до MVP

## Этап A — Audit + state transitions (2–3 дня)
- Добавить модель/миграции `audit_logs`.
- Формализовать state machine переходов.
- Логировать смены статусов и назначения.

## Этап B — User Conversation API completion (1–2 дня)
- `GET /conversations` (фильтры, пагинация).
- `POST /conversations/{id}/close`.
- Проверки изоляции и прав для новых действий.

## Этап C — AI adapter и routing (2–3 дня)
- Интерфейс LLM adapter + OpenAI реализация.
- Асинхронный pipeline.
- Confidence routing и fallback-эскалация.

## Этап D — Operator API (1–2 дня)
- Очередь эскалаций.
- API для assign/reply/close/back_to_ai.
- Ограничение активных диалогов на оператора.

## Этап E — Observability + polishing (1–2 дня)
- JSON-логи и метрики.
- Health + readiness.
- Обновление README/runbook.

---

## 5) Остаточная оценка сроков

- **Осталось: 6–10 рабочих дней**.
- **Оптимистично:** 6–7 дней.
- **Реалистично:** 8–10 дней.

---

## 6) Критерий завершения текущего этапа (checkpoint)

Текущий этап (**user/auth + conversations + messages basic**) считается завершённым, когда:
- message-поток стабилен (create/list) для авторизованных участников диалога;
- покрыты тестами схемы/сервисы/репозитории/роутеры по сообщениям;
- зафиксирован backlog на `audit/state machine/AI/operator`.

**Checkpoint status: достигнут; следующий фокус — Audit + state machine.**
