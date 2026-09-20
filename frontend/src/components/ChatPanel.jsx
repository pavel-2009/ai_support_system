import { useEffect, useRef, useState } from 'react';
import { statusLabels } from './ConversationList';

const formatTime = (value) => new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' }).format(new Date(value));

function Message({ message, userId }) {
  const own = message.sender_id === userId;
  const sender = message.sender_type === 'ai' ? '✦ AI-ассистент' : message.sender_type === 'operator' ? 'Оператор' : own ? 'Вы' : 'Клиент';
  return <div className={`message-line ${own ? 'outgoing' : ''}`}>
    <article className={`message ${message.sender_type === 'ai' ? 'ai-message' : ''}`}>
      <b>{sender}</b><p>{message.content}</p><small>{formatTime(message.created_at)}{message.confidence ? ` · уверенность ${Math.round(message.confidence * 100)}%` : ''}</small>
    </article>
  </div>;
}

function Composer({ onSend, disabled }) {
  const [value, setValue] = useState('');
  async function submit(event) {
    event.preventDefault();
    const content = value.trim();
    if (!content || disabled) return;
    setValue('');
    try { await onSend(content); } catch { setValue(content); }
  }
  return <form className="composer" onSubmit={submit}>
    <textarea value={value} onChange={(event) => setValue(event.target.value)} placeholder="Напишите сообщение…" rows="1" disabled={disabled} />
    <button className="send" aria-label="Отправить" disabled={!value.trim() || disabled}>{disabled ? '…' : '↑'}</button>
  </form>;
}

const statusHelp = {
  open: 'Сообщение обрабатывается системой',
  pending_ai: 'AI формирует ответ',
  waiting_for_operator: 'Обращение ожидает оператора',
  waiting_for_user: 'Ожидается ваш ответ',
  escalated: 'Обращение передано оператору',
  closed: 'Диалог завершён',
};

export function ChatPanel({ conversation, messages, userId, isLoading, isSending, onSend, readOnly = false }) {
  const lastMessageRef = useRef(null);
  const previousStatus = useRef(conversation?.status);
  useEffect(() => {
    if (!messages.length && !isSending) return;
    lastMessageRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, isSending]);
  useEffect(() => {
    previousStatus.current = conversation?.status;
  }, [conversation?.status]);

  if (!conversation) return <section className="empty-state"><div>✦</div><h2>Выберите диалог</h2><p>История обращения появится здесь.</p></section>;

  const status = statusLabels[conversation.status] || conversation.status;
  const disabled = readOnly || isSending || conversation.status === 'closed';

  return <section className="chat">
    <header className="chat-header">
      <div><p className="eyebrow">ОБРАЩЕНИЕ #{conversation.id}</p><h2>Поддержка</h2><p className="status-help">{statusHelp[conversation.status]}</p></div>
      <span key={conversation.status} className={`pill status-change ${conversation.status}`}>{status}</span>
    </header>
    <div className="messages" aria-busy={isLoading}>
      {isLoading && <p className="muted">Загружаем сообщения…</p>}
      {messages.map((message) => <Message key={message.id} message={message} userId={userId} />)}
      {isSending && <div className="message-line"><div className="typing"><span>✦</span><i /><i /><i /><small>AI-ассистент формулирует ответ</small></div></div>}
      {!isLoading && !messages.length && <div className="empty-messages"><span>✦</span><p>Начните диалог — мы здесь.</p></div>}
      <div ref={lastMessageRef} />
    </div>
    {!readOnly && <Composer onSend={onSend} disabled={disabled} />}
  </section>;
}
