# PLAN — AI Support System (актуализация на 19 апреля 2026)

## 1) Текущий статус проекта

Проект находится на этапе **стабильного MVP+ по user/auth/conversations/messages**.

Ключевые обновления текущего состояния:
- CI вынесен в корневой `.github/workflows/ci.yml`, чтобы workflow гарантированно запускался в GitHub Actions.
- CI адаптирован под фактическую структуру репозитория (рабочая директория `app/`, корректные пути к артефактам).
- `/api/auth/login` поддерживает и JSON-логин (email/password), и OAuth2 form-login (username/password) для Swagger.
- Текущее состояние проекта подтверждено тестами: **85/85 passed**.

### Процент готовности

- **Оценка выполненной работы: ~82%**.
- **Оставшийся объём: ~18%**.

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
- [x] Ролевая изоляция для user/admin на текущих эндпоинтах.
- [x] Совместимый логин для API-клиентов и Swagger (JSON + OAuth2 form).
- [~] Operator-сценарии остаются частичными.

### 2.4 API поддержки
- [x] `POST /api/conversations/`.
- [x] `GET /api/conversations/{id}` (с `410` для closed).
- [x] `GET /api/conversations/{id}/messages`.
- [x] `POST /api/conversations/{id}/messages`.
- [x] `GET /api/conversations/queue/active`.
- [x] `GET /api/conversations` (фильтры + пагинация).
- [x] `POST /api/conversations/{id}/close`.

### 2.5 CI/CD и качество
- [x] CI workflow перенесён в корень репозитория и запускается корректно.
- [x] Сбор артефактов `coverage.xml` и `pytest-report.xml` настроен на актуальные пути.
- [x] Все тесты в текущем состоянии зелёные (`85 passed`).

---

## 3) Что не реализовано (Gap к MVP)

1. **Operator workflow (полный)**
   - Нет отдельного полного контура: `assign/reply/close/back_to_ai`.
   - Нет лимита активных диалогов на оператора.

2. **AI processing (production-ready)**
   - Нет завершённого фонового orchestration-пайплайна.
   - Нет полного confidence-routing в production-потоке.

3. **Observability / эксплуатация**
   - Нет метрик Prometheus/readiness-probe.
   - Нет дашбордов/алертинга.

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
- Централизовать переходы статусов (единый transition слой).
- Явно валидировать допустимые переходы.

## Этап D — AI adapter и routing (2–3 дня)
- Интерфейс LLM adapter + OpenAI реализация.
- Асинхронный pipeline для AI-взаимодействий.

## Этап E — Observability + polishing (1–2 дня)
- Метрики и readiness.
- Runbook/README polishing.
- Базовые smoke/e2e проверки operator-потока в CI.

---

## 5) Остаточная оценка сроков

- **Осталось: 3–6 рабочих дней**.
- **Оптимистично:** 3–4 дня.
- **Реалистично:** 5–6 дней.

---

## 6) Критерий завершения текущего checkpoint

Checkpoint «стабилизация после рефакторинга» считается завершённым:
- [x] CI расположен и работает из корня репозитория.
- [x] Локально проект проходит тесты в текущем состоянии.
- [x] Логин совместим с текущими тестами и Swagger.

**Checkpoint status: завершён, следующий фокус — operator workflow + state machine hardening + AI pipeline + observability.**
