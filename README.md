<aside>
<img src="i" alt="i" width="40px" />

**Техническое задание**


AI Support System (аналог Intercom / Zendesk) • Версия 1.0

</aside>

- Тип проекта: Backend-сервис
- Сложность: Middle+ / Senior
- Ожидаемый срок: 2–3 недели (full-time)

---

## 1. Цель проекта

Разработать backend-систему поддержки пользователей с AI-агентами, которая:

- принимает сообщения через REST API
- автоматически отвечает с помощью LLM (OpenAI или аналог)
- эскалирует сложные вопросы операторам
- управляет состояниями диалогов и очередями
- предоставляет API для операторов

Ключевая фича: интеллектуальная маршрутизация сообщений на основе уверенности AI.

---

## 2. Функциональные требования

### 2.1. Пользователи и роли

<aside>
<img src="i" alt="i" width="40px" />

**Роли**

</aside>

- Пользователь: создавать диалоги, отправлять сообщения, получать ответы
- Оператор: просматривать очередь, брать диалоги, отвечать, закрывать
- Админ: всё, что может оператор + просмотр логов/метрик, управление AI

Требования:

- регистрация пользователей (email + пароль)
- JWT-аутентификация
- операторы создаются только админом (или через seed)

---

### 2.2. Диалоги (Conversations)

Поля:

```
id               UUID
user_id          UUID (FK)
operator_id      UUID (FK, nullable)
status           enum
priority         enum (low, medium, high)
channel          enum (web, api, email)
ai_confidence    float (nullable)
created_at       timestamp
updated_at       timestamp
closed_at        timestamp (nullable)
```

Статусы (строгое состояние):

```
open                 → AI отвечает
waiting_for_user     → ждём ответа пользователя
waiting_for_operator → оператор назначен, но не ответил
escalated            → передан оператору (ждёт в очереди)
pending_ai           → AI обрабатывает (технический)
closed               → диалог завершён
```

Правила смены статусов:

- пользователь пишет → open (если был waiting_for_user)
- AI не уверен (< 0.6) → escalated
- оператор взял → waiting_for_operator
- оператор ответил → waiting_for_user
- пользователь не отвечает 3 часа → closed
- оператор закрыл → closed

---

### 2.3. Сообщения (Messages)

Поля:

```
id               UUID
conversation_id  UUID (FK)
sender_type      enum (user, ai, operator)
sender_id        UUID (nullable для AI)
content          text
is_auto_reply    boolean (true для AI)
confidence       float (nullable, только для AI)
needs_review     boolean (true если confidence < 0.85)
created_at       timestamp
```

Правила:

- сообщение пользователя → триггерит AI-обработку
- AI отвечает → is_auto_reply=true
- оператор отвечает → sender_type=operator
- история сообщений хранится бессрочно

---

### 2.4. AI-логика (ключевая)

#### 2.4.1. Алгоритм обработки

```
1. Получить последние 5 сообщений диалога (контекст)
2. Отправить в LLM с промптом:
   - Ответь на вопрос пользователя
   - Если не знаешь → confidence < 0.6
   - Если частично знаешь → 0.6–0.85
   - Если уверен → > 0.85
3. Получить {answer, confidence, topic}
4. Принять решение:
   - confidence > 0.85 → отправить ответ
   - 0.6–0.85 → отправить + пометить needs_review
   - < 0.6 → НЕ отвечать, эскалировать
```

#### 2.4.2. Эскалация (escalation)

При эскалации:

- статус диалога → escalated
- диалог попадает в очередь операторов
- создаётся событие в audit_log
- (опционально) WebSocket уведомление операторам

#### 2.4.3. Требования к LLM

- поддержка OpenAI API (GPT-3.5/4)
- возможность заменить на локальную модель (Ollama / Mistral)
- таймаут запроса: 5 секунд
- retry: 2 раза при ошибке

---

### 2.5. Очередь операторов

API для оператора:

- GET /api/v1/operator/queue — список escalated диалогов (сортировка по приоритету и времени)
- POST /api/v1/operator/assign/{conversation_id} — взять диалог в работу
- POST /api/v1/operator/reply/{conversation_id} — ответить пользователю
- POST /api/v1/operator/close/{conversation_id} — закрыть диалог
- POST /api/v1/operator/back_to_ai/{conversation_id} — вернуть AI-обработку

Правила:

- один оператор может вести до 5 активных диалогов
- оператор видит всю историю диалога
- после ответа оператора AI не отвечает, пока пользователь не напишет снова

---

### 2.6. API для пользователя

- POST /api/v1/conversations — создать новый диалог
- GET /api/v1/conversations — список своих диалогов
- GET /api/v1/conversations/{id}/messages — получить сообщения
- POST /api/v1/conversations/{id}/messages — отправить сообщение
- POST /api/v1/conversations/{id}/close — закрыть диалог (пользователь)

Особенности:

- при создании диалога → статус open
- первое сообщение отправляется вместе с созданием (либо отдельно)

---

## 3. Нефункциональные требования

### 3.1. Производительность

- ответ API на сообщение (без AI) < 50 мс
- AI-обработка асинхронная (не блокирует API)
- поддержка до 100 сообщений в секунду

### 3.2. Надёжность

- AI-запросы с retry и fallback (если AI упал → сразу эскалация)
- все внешние вызовы с timeout
- graceful shutdown

### 3.3. Наблюдаемость

- логи всех AI-решений (confidence, latency)
- метрики (Prometheus):
    - количество эскалаций
    - средний confidence
    - задержки AI
    - размер очереди операторов
- audit log (кто и когда менял статус диалога)

### 3.4. Безопасность

- все эндпоинты (кроме регистрации) требуют JWT
- операторы не видят чужие диалоги
- пользователь видит только свои диалоги

---

## 4. Технический стек (рекомендованный)

- Язык: Python 3.11+ / Go / Node.js (на выбор)
- Фреймворк: FastAPI / Echo / Express
- БД: PostgreSQL 15+
- Кеш / очереди: Redis (для AI-задач)
- AI: OpenAI API + адаптер под локальные модели
- Аутентификация: JWT (access + refresh)
- WebSockets: для уведомлений операторов (опционально)
- Метрики: Prometheus + Grafana
- Логи: JSON logs (stdout)

---

## 5. База данных (схема)

```sql
-- пользователи
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- диалоги
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    operator_id UUID REFERENCES users(id),
    status VARCHAR(50) NOT NULL,
    priority VARCHAR(50) DEFAULT 'medium',
    channel VARCHAR(50) DEFAULT 'web',
    ai_confidence FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    closed_at TIMESTAMP
);

-- сообщения
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    sender_type VARCHAR(20) NOT NULL,
    sender_id UUID REFERENCES users(id),
    content TEXT NOT NULL,
    is_auto_reply BOOLEAN DEFAULT false,
    confidence FLOAT,
    needs_review BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- AI-логи (для аналитики)
CREATE TABLE ai_decisions (
    id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id),
    message_id UUID REFERENCES messages(id),
    confidence_score FLOAT NOT NULL,
    decision VARCHAR(50) NOT NULL,
    reason TEXT,
    model_used VARCHAR(100),
    latency_ms INT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- аудит
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    action VARCHAR(255) NOT NULL,
    entity_type VARCHAR(50),
    entity_id UUID,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

Индексы:

- conversations(user_id, status)
- messages(conversation_id, created_at)
- conversations(status, priority, created_at) — для очереди
- audit_logs(created_at)

---

## 6. Последовательность работы (примеры)

### Сценарий 1: AI отвечает

```
1. POST /conversations/{id}/messages (user)
2. Сохраняем сообщение
3. Отправляем в Redis-очередь AI-задачу
4. Возвращаем 202 Accepted (сообщение принято)
5. Worker обрабатывает:
   - вызывает LLM
   - confidence = 0.92
   - сохраняет AI-ответ
   - отправляет WebSocket пользователю (опционально)
6. Пользователь получает ответ через polling / ws
```

### Сценарий 2: Эскалация

```
1. Сообщение пользователя
2. AI вернул confidence = 0.45
3. Статус диалога → escalated
4. Диалог появляется в /operator/queue
5. Оператор берёт через assign
6. Статус → waiting_for_operator
7. Оператор отвечает
8. Статус → waiting_for_user
```

### Сценарий 3: Таймаут

```
1. Диалог в waiting_for_user
2. Пользователь не пишет 3 часа
3. Cron-джоб / фоновый процесс:
   - находит такие диалоги
   - закрывает их (status = closed)
   - пишет системное сообщение (опционально)
```

---

## 7. Требования к документации

Разработчик обязан предоставить:

1. [README.md](http://README.md)
    - как поднять проект (docker-compose)
    - переменные окружения
    - примеры запросов
2. OpenAPI спецификация (swagger.yaml)
    - все эндпоинты с примерами
3. Диаграмма состояний (state machine)
    - статусы диалога и переходы
4. Sequence diagram для AI-обработки
5. Инструкция по деплою (docker + CI/CD пример)

---

## 8. Критерии приёмки

Проект принимается, если:

- ✅ все API работают по спецификации
- ✅ AI отвечает с confidence > 0.85
- ✅ эскалация работает при low confidence
- ✅ оператор может взять и ответить
- ✅ очередь сортируется по приоритету и времени
- ✅ состояния диалога меняются корректно
- ✅ есть audit log
- ✅ написаны интеграционные тесты (минимум 5 сценариев)
- ✅ проект запускается через docker-compose up

---

## 9. Бонусы

- WebSockets для realtime уведомлений
- Dashboard для операторов (минимальный React/Vue)
- Авто-тегирование сообщений (billing, bug, etc)
- Поддержка file attachments (ссылки на файлы)
- Экспорт диалогов в JSON/CSV
- Система шаблонов для частых ответов

---

## 10. Примеры API (REST)

### Отправить сообщение

```
POST /api/v1/conversations/123/messages
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "Как сменить пароль?"
}
```

Ответ (202):

```json
{
  "message_id": "msg-456",
  "status": "processing",
  "will_be_processed_by": "ai"
}
```

### Очередь оператора

```
GET /api/v1/operator/queue?limit=20
Authorization: Bearer <operator_token>
```

Ответ:

```json
{
  "queue": [
    {
      "conversation_id": "conv-789",
      "user_email": "user@example.com",
      "priority": "high",
      "created_at": "2024-01-01T10:00:00Z",
      "last_message": "Всё сломалось!",
      "ai_confidence": 0.32
    }
  ]
}
```