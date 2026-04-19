# PLAN — AI Support System (актуализация на 17 апреля 2026)

## 1) Текущий статус проекта

Проект на этапе **завершения MVP по user/auth/conversations/messages**:

- Реализованы пользовательские роутеры в `app/routers/users` с сохранением текущих API-префиксов.
- Добавлены `GET /api/conversations` (базовые фильтры + пагинация) и `POST /api/conversations/{id}/close`.
- Усилены проверки доступа: для conversations доступ только админу или участнику диалога.
- Добавлена проверка статуса закрытого диалога: `410 Gone` при запросе закрытого диалога и его сообщений.
- Расширен `/health`: проверяются API, БД, Redis, Celery.
- Добавлено централизованное логирование и подробные сообщения об ошибках с traceback.

### Процент готовности

- **Оценка выполненной работы: ~75%**.
- **Оставшийся объём: ~25%**.

---

## 2) Что уже сделано (Done)

### 2.1 Foundation
- [x] Базовый FastAPI app + health-check.
- [x] Разделение на слои `core`, `routers`, `services`, `repositories`, `schemas`, `models`.
- [x] Централизованное логирование.

### 2.2 Данные
- [x] `users`, `conversations`, `messages`.
- [x] `audit_logs`, `conversation_operator_links`.

### 2.3 Auth и доступ
- [x] JWT access/refresh.
- [x] Общий доступ к обычным защищённым эндпоинтам для авторизованных.
- [x] Отдельные функции проверки прав для conversations.
- [~] Operator-сценарии остаются частичными.

### 2.4 API поддержки
- [x] `POST /api/conversations/`.
- [x] `GET /api/conversations/{id}` (с `410` для closed).
- [x] `GET /api/conversations/{id}/messages`.
- [x] `POST /api/conversations/{id}/messages`.
- [x] `GET /api/conversations/queue/active`.
- [x] `GET /api/conversations` (фильтры + пагинация).
- [x] `POST /api/conversations/{id}/close`.

### 2.5 Качество
- [x] Обновлены unit-тесты под новые conversations/health-поведения.
- [x] Добавлены тесты на `410 Gone` и новые проверки прав.

---

## 3) Что не реализовано (Gap к MVP)

1. **Operator workflow (полный)**
   - Нет API: `assign/reply/close/back_to_ai` как отдельного operator-контура.
   - Нет лимита активных диалогов на оператора.

2. **AI processing (production-ready)**
   - Нет полного фонового orchestration-пайплайна.
   - Нет полного confidence routing в бизнес-потоке.

3. **Observability / эксплуатация**
   - Нет метрик Prometheus/readiness-probe.
   - Нет полноценных дашбордов и алертинга.

---

## 4) Обновлённый план до MVP

## Этап A — Conversation API completion
- [x] `GET /conversations` (фильтры, пагинация).
- [x] `POST /conversations/{id}/close` (user).
- [x] Проверки изоляции и прав для conversations.

## Этап B — Operator workflow completion (2–3 дня)
- `POST /operator/assign/{conversation_id}`.
- `POST /operator/reply/{conversation_id}`.
- `POST /operator/close/{conversation_id}`.
- `POST /operator/back_to_ai/{conversation_id}`.

## Этап C — State machine hardening (1–2 дня)
- Валидация допустимых переходов статусов.
- Централизация transition-логики.

## Этап D — AI adapter и routing (2–3 дня)
- Интерфейс LLM adapter + OpenAI реализация.
- Асинхронный pipeline для AI-взаимодействий.

## Этап E — Observability + polishing (1–2 дня)
- Метрики и readiness.
- Runbook/README polishing.

---

## 5) Остаточная оценка сроков

- **Осталось: 4–7 рабочих дней**.
- **Оптимистично:** 4–5 дней.
- **Реалистично:** 6–7 дней.

---

## 6) Критерий завершения текущего checkpoint

Checkpoint по conversations считается завершённым:
- [x] Список диалогов доступен с простой фильтрацией и пагинацией.
- [x] Закрытие диалога доступно участнику/админу.
- [x] Закрытые диалоги возвращают `410` на чтение диалога и сообщений.
- [x] Доступ к conversations централизован и изолирован через зависимости.

**Checkpoint status: завершён, следующий фокус — operator workflow + state machine hardening + AI pipeline.**
