# PLAN — AI Support System (актуализация на 15 апреля 2026)

## 1) Текущий статус проекта

Проект находится на этапе **user/auth + базовый контур conversations**:

- Реализована FastAPI-архитектура по слоям (`routers/services/repositories/models/schemas`).
- Реализованы `users` и `conversations` (модели, репозитории, сервисы, роутеры).
- Реализованы auth-flow: `register`, `login`, `refresh`, `logout`.
- Реализованы RBAC-проверки для user/admin в user- и conversation-endpoint.
- Набор unit/e2e тестов расширен: покрыты ключевые позитивные и негативные сценарии сервисов и роутеров.

### Процент готовности

- **Оценка выполненной работы: ~35%**.
- **Оставшийся объем: ~65%**.

> Почему 35%: кроме user/auth фундамента закрыт минимальный workflow диалогов (`create/get` + доступ), но всё ещё отсутствует основной MVP-функционал: сообщения, операторский цикл, AI-routing, аудит и метрики.

---

## 2) Что уже сделано (Done)

### 2.1 Foundation
- [x] Базовый FastAPI app + роутеры + health-check.
- [x] Разделение на слои `core`, `routers`, `services`, `repositories`, `schemas`, `models`.
- [x] Базовая конфигурация через settings.

### 2.2 Данные
- [x] Модель `users` + миграции.
- [x] Модель `conversations` + базовые enum-поля (status/priority/channel).
- [ ] `messages`, `audit_logs` — не реализованы.

### 2.3 Auth и доступ
- [x] Регистрация.
- [x] JWT access/refresh.
- [x] Логин + refresh endpoint.
- [x] RBAC для admin/user.
- [~] Частично: права для operator-сценариев и продвинутая изоляция по workflow не завершены.

### 2.4 API поддержки
- [x] `POST /api/conversations/`.
- [x] `GET /api/conversations/{id}`.
- [ ] Список диалогов пользователя.
- [ ] Работа с сообщениями (`list/create`).
- [ ] Close/reopen/status transition API.

### 2.5 Качество
- [x] Unit/e2e тесты для user/auth.
- [x] Дополнительные unit/e2e тесты для сервисов и роутеров users/conversations.
- [x] Текущий ориентир покрытия: **~91%** по `app/main` (по локальному запуску `pytest --cov`).

---

## 3) Что не реализовано (Gap к MVP)

Критичные незакрытые зоны:

1. **Домен поддержки**
   - Нет сущности сообщений в диалогах.
   - Нет аудита действий (кто/когда сменил статус, назначил оператора и т.д.).

2. **AI processing**
   - Нет LLM adapter и pipeline обработки.
   - Нет confidence routing (`>0.85`, `0.6–0.85`, `<0.6`).
   - Нет timeout/retry/fallback-эскалации.

3. **Operator workflow**
   - Нет очереди эскалаций.
   - Нет `assign/reply/close/back_to_ai` API.
   - Нет лимита активных диалогов на оператора.

4. **Observability / эксплуатация**
   - Нет audit log.
   - Нет метрик Prometheus.
   - Нет readiness endpoint и расширенной диагностики.

5. **Документация и demo readiness**
   - README пока отражает базовый run/setup, но не full MVP runbook.
   - Нет seed/demo-сценариев полного цикла user→AI→operator.

---

## 4) Обновленный план до MVP Portfolio Ready

## Этап A — Messages + audit data model (2–3 дня)
- Добавить модели/миграции:
  - `messages`
  - `audit_logs`
- Связать `messages` с `conversations/users`.
- Добавить репозитории и схемы.

**Результат:** можно хранить историю переписки и событий.

## Этап B — User Conversation API completion (2 дня)
- `GET /conversations` (фильтры, пагинация)
- `GET /conversations/{id}/messages`
- `POST /conversations/{id}/messages`
- `POST /conversations/{id}/close`
- Проверка изоляции и прав.

**Результат:** завершён пользовательский контур поддержки.

## Этап C — State machine + audit writing (1–2 дня)
- Формализовать допустимые переходы статусов.
- Вынести правила переходов в service-слой.
- Писать каждую смену статуса в `audit_logs`.

**Результат:** предсказуемая и проверяемая бизнес-логика.

## Этап D — AI adapter и routing (2–3 дня)
- Интерфейс LLM adapter + OpenAI реализация.
- Асинхронный pipeline (background worker/queue).
- Confidence routing и fallback-эскалация.

**Результат:** рабочая AI-маршрутизация + эскалация.

## Этап E — Operator API (1–2 дня)
- `GET /operator/queue`
- `POST /operator/assign/{conversation_id}`
- `POST /operator/reply/{conversation_id}`
- `POST /operator/close/{conversation_id}`
- `POST /operator/back_to_ai/{conversation_id}`
- Лимит до 5 активных диалогов на оператора.

**Результат:** полноценный операторский контур.

## Этап F — Observability + polishing (1–2 дня)
- JSON logs для AI-решений.
- Prometheus метрики (escalations, confidence avg, AI latency, queue size).
- Health + readiness.
- Обновление README (архитектура, запуск, примеры API).

**Результат:** MVP готов к демонстрации и портфолио.

---

## 5) Остаточная оценка сроков

При текущем состоянии:

- **Осталось: 8–12 рабочих дней** (full-time 6–8 ч/день).
- **Оптимистично:** 8–9 дней.
- **Реалистично:** 10–12 дней.

---

## 6) Риски и приоритеты на ближайшие шаги

### Топ-риски
- Несогласованность статусов при параллельных событиях (AI/оператор/user).
- Нестабильность внешнего AI API.
- Перерасход времени из-за premature production-hardening.

### Приоритеты ближайшего спринта
1. Сначала закрыть **messages + state machine + audit**.
2. Затем закончить **user conversation API**.
3. После — **AI routing**, и только затем **operator queue/API**.

---

## 7) Критерий завершения текущего этапа (checkpoint)

Текущий этап (**user/auth + basic conversations**) считается завершённым, когда:
- user/auth/conversation сервисы и роутеры покрыты тестами на базовые happy/error path;
- текущий тестовый пакет стабилен локально;
- зафиксирован следующий backlog на `messages/state machine/audit`.

**Checkpoint status: почти достигнут; следующий фокус — Этап A (messages + audit model).**
