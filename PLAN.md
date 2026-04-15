# PLAN — AI Support System (актуализация на 15 апреля 2026)

## 1) Текущий статус проекта

Проект находится на этапе **базового user/auth ядра**:

- Реализован FastAPI-приложение и базовая структура слоев (`routers/services/repositories/models/schemas`).
- Реализованы `users` + миграция Alembic только для таблицы пользователей.
- Реализованы auth-flow: `register`, `login`, `refresh`, `logout`.
- Реализованы RBAC-ограничения для admin/user в рамках пользовательских endpoint.
- Есть health-check endpoint и набор unit/e2e тестов, которые проходят.

### Процент готовности

- **Оценка выполненной работы: ~25%**.
- **Оставшийся объем: ~75%**.

> Почему 25%: закрыт фундамент (аутентификация/пользователи/каркас), но отсутствуют ключевые бизнес-фичи ТЗ — conversations/messages, AI-routing, escalation queue, operator API, audit/metrics/readiness.

---

## 2) Что уже сделано (Done)

### 2.1 Foundation
- [x] Базовый FastAPI app + роутеры + health-check.
- [x] Разделение на слои `core`, `routers`, `services`, `repositories`, `schemas`, `models`.
- [x] Базовая конфигурация через settings.

### 2.2 Данные
- [x] Модель `users`.
- [x] Первая миграция Alembic для `users`.
- [ ] `conversations`, `messages`, `audit_logs` — не реализованы.

### 2.3 Auth и доступ
- [x] Регистрация.
- [x] JWT access/refresh.
- [x] Логин + refresh endpoint.
- [x] Базовый RBAC для admin/user.
- [~] Не завершено в полном объеме ТЗ (нет привязки прав к диалогам/операторским объектам).

### 2.4 Качество
- [x] Базовый набор unit/e2e тестов для user/auth части.
- [x] Добавлено покрытие unit-тестами:
  - инициализации сервисов (`services_init`) и `lifespan` старта приложения;
  - роутеров `users/auth` и `conversations` (ключевые ветки доступа/ошибок);
  - сервисов `ConversationService` и instance-логики `UserService`.
- [~] Полный `pytest` по репозиторию пока не green: есть legacy-регрессии вне добавленного скоупа (ORM-связи/часть старых тестов).

---

## 3) Что не реализовано (Gap к MVP)

Критичные незакрытые зоны:

1. **Домен поддержки**
   - Нет сущностей диалогов и сообщений.
   - Нет state machine статусов диалога.

2. **AI processing**
   - Нет LLM adapter и pipeline обработки.
   - Нет confidence routing (`>0.85`, `0.6–0.85`, `<0.6`).
   - Нет timeout/retry/fallback-эскалации.

3. **Operator workflow**
   - Нет очереди эскалаций.
   - Нет `assign/reply/close/back_to_ai`.
   - Нет лимита активных диалогов на оператора.

4. **Observability / эксплуатация**
   - Нет audit log смен статусов.
   - Нет метрик Prometheus.
   - Нет readiness endpoint и расширенной диагностики.

5. **Документация и demo readiness**
   - README пока отражает ТЗ, но не полноценный runbook MVP.
   - Нет seed-сценариев для operator/admin демонстрации в полном домене.

---

## 4) Обновленный план до MVP Portfolio Ready

## Этап A — Домен поддержки (2–3 дня)
- Добавить модели/миграции:
  - `conversations`
  - `messages`
  - `audit_logs`
- Ввести enums: статусы, приоритет, канал, sender_type.
- Добавить репозитории и базовые схемы.

**Результат:** можно хранить и читать диалоги/сообщения.

## Этап B — User Conversation API (2 дня)
- `POST /conversations`
- `GET /conversations`
- `GET /conversations/{id}/messages`
- `POST /conversations/{id}/messages`
- `POST /conversations/{id}/close`
- Проверка изоляции: пользователь видит только свои диалоги.

**Результат:** закрыт пользовательский контур поддержки.

## Этап C — State machine + audit (1–2 дня)
- Формализовать допустимые переходы статусов.
- Вынести правила в service-слой.
- Записывать каждую смену статуса в `audit_logs`.

**Результат:** предсказуемая и проверяемая бизнес-логика.

## Этап D — AI adapter и routing (2–3 дня)
- Реализовать интерфейс LLM adapter + OpenAI реализацию.
- Добавить асинхронный pipeline (background worker/queue).
- Реализовать confidence routing и fallback.

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
- JSON logs для AI решений.
- Prometheus метрики (escalations, confidence avg, AI latency, queue size).
- Health + readiness.
- Обновление README (архитектура, запуск, примеры API).

**Результат:** MVP готов к демонстрации и портфолио.

---

## 5) Остаточная оценка сроков

При текущем состоянии:

- **Осталось: 9–14 рабочих дней** (full-time 6–8 ч/день).
- **Оптимистично:** 9–10 дней (если без сложных инфраструктурных блокеров).
- **Реалистично:** 11–14 дней (с учетом отладки AI-интеграции и стабилизации тестов).

---

## 6) Риски и приоритеты на ближайшие шаги

### Топ-риски
- Непростая согласованность статусов при параллельных событиях (AI/оператор/user).
- Нестабильность внешнего AI API.
- Рост времени реализации из-за попытки “сделать сразу production”.

### Приоритеты ближайшего спринта
1. Сначала закрыть **данные + state machine**.
2. Потом **user conversation API**.
3. Только затем подключать **AI и operator queue**.

Такой порядок минимизирует переделки и снижает риск регрессий.

---

## 7) Критерий завершения текущего этапа (checkpoint)

Текущий этап (user/auth foundation) считается завершенным, когда:
- все auth/user тесты зеленые;
- миграции и модель `users` стабильны;
- зафиксирован и согласован следующий backlog по conversations/AI/operator.

**Checkpoint status: частично достигнут.**

- Каркас и auth/user функциональность реализованы.
- Покрытие unit-тестами расширено (роутеры/сервисы/startup lifecycle).
- Для полного закрытия checkpoint нужно стабилизировать legacy-тесты и ORM-связи, после чего зафиксировать green full test run.
