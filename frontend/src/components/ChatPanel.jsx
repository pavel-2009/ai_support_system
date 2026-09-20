import { useEffect, useRef, useState } from 'react';
import { statusLabels } from './ConversationList';

const formatTime = (value) => {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? ''
    : new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' }).format(date);
};

function Message({ message, userId }) {
  const own = message.sender_id === userId;
  const sender = message.sender_type === 'ai'
    ? '✦ AI-ассистент'
    : message.sender_type === 'operator'
      ? 'Оператор'
      : own ? 'Вы' : 'Клиент';

  return (
    <div className={`message-line ${own ? 'outgoing' : ''}`}>
      <article className={`message ${message.sender_type === 'ai' ? 'ai-message' : ''}`}>
        <b>{sender}</b>
        <p>{message.content}</p>
        <small>
          {formatTime(message.created_at)}
          {typeof message.confidence === 'number'
            ? ` · уверенность ${Math.round(message.confidence * 100)}%`
            : ''}
        </small>
      </article>
    </div>
  );
}

function Composer({ onSend, disabled, autoFocus = false }) {
  const [value, setValue] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    if (!autoFocus || disabled) return;
    const frame = window.requestAnimationFrame(() => inputRef.current?.focus());
    return () => window.cancelAnimationFrame(frame);
  }, [autoFocus, disabled]);

  async function submit(event) {
    event.preventDefault();
    const content = value.trim();
    if (!content || disabled || submitting) return;

    setSubmitting(true);
    try {
      await onSend(content);
      setValue('');
    } catch {
      // Keep the text only when the request failed.
    } finally {
      setSubmitting(false);
    }
  }

  const blocked = disabled || submitting;

  return (
    <form className="composer" onSubmit={submit}>
      <textarea
        ref={inputRef}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="Напишите сообщение…"
        rows={1}
        maxLength={10000}
        disabled={blocked}
        aria-label="Сообщение"
      />
      <button
        type="submit"
        className="send"
        aria-label="Отправить"
        disabled={!value.trim() || blocked}
      >
        {blocked ? '…' : '↑'}
      </button>
    </form>
  );
}

const statusHelp = {
  open: 'Сообщение обрабатывается системой',
  pending_ai: 'AI формирует ответ',
  waiting_for_operator: 'Обращение ожидает оператора',
  waiting_for_user: 'Ожидается ваш ответ',
  escalated: 'Обращение передано оператору',
  closed: 'Диалог завершён',
};

const userBlockedStatuses = new Set([
  'closed',
  'escalated',
  'waiting_for_operator',
  'pending_ai',
]);

export function ChatPanel({
  conversation,
  messages = [],
  userId,
  isLoading = false,
  isSending = false,
  isAiGenerating = false,
  onSend,
  readOnly = false,
  operatorMode = false,
  autoFocusComposer = false,
}) {
  const lastMessageRef = useRef(null);
  const lastMessageIdRef = useRef(null);

  useEffect(() => {
    const lastMessageId = messages.at(-1)?.id;
    if (!lastMessageId || lastMessageId === lastMessageIdRef.current) return;

    const firstRender = lastMessageIdRef.current === null;
    lastMessageIdRef.current = lastMessageId;
    lastMessageRef.current?.scrollIntoView({
      behavior: firstRender ? 'auto' : 'smooth',
      block: 'end',
    });
  }, [messages]);

  useEffect(() => {
    if (!conversation) lastMessageIdRef.current = null;
  }, [conversation?.id]);

  if (!conversation) {
    return (
      <section className="empty-state">
        <div>✦</div>
        <h2>Выберите диалог</h2>
        <p>История обращения появится здесь.</p>
      </section>
    );
  }

  const status = statusLabels[conversation.status] || conversation.status;
  const showAiTyping =
    Boolean(isAiGenerating) &&
    conversation.status === 'pending_ai' &&
    !readOnly;

  const disabled =
    readOnly ||
    isSending ||
    showAiTyping ||
    (!operatorMode && userBlockedStatuses.has(conversation.status));

  return (
    <section className="chat">
      <header className="chat-header">
        <div>
          <p className="eyebrow">ОБРАЩЕНИЕ #{conversation.id}</p>
          <h2>Поддержка</h2>
          <p className="status-help">{statusHelp[conversation.status] || 'Текущее состояние диалога'}</p>
        </div>
        <span className={`pill ${conversation.status}`}>{status}</span>
      </header>

      <div className="messages" aria-busy={isLoading || showAiTyping}>
        {isLoading && <p className="muted">Загружаем сообщения…</p>}
        {messages.map((message) => (
          <Message key={message.id} message={message} userId={userId} />
        ))}

        {showAiTyping && (
          <div className="message-line">
            <div className="typing" role="status" aria-label="AI формирует ответ">
              <span>✦</span><i /><i /><i />
              <small>AI-ассистент формулирует ответ</small>
            </div>
          </div>
        )}

        {!isLoading && !messages.length && (
          <div className="empty-messages">
            <span>✦</span>
            <p>Начните диалог — мы здесь.</p>
          </div>
        )}
        <div ref={lastMessageRef} />
      </div>

      {!readOnly && <Composer onSend={onSend} disabled={disabled} autoFocus={autoFocusComposer} />}
    </section>
  );
}
