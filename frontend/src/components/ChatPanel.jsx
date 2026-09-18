import { useEffect, useRef, useState } from 'react';
import { statusLabels } from './ConversationList';

const formatTime = (value) => new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' }).format(new Date(value));

function Message({ message, userId }) {
  const own = message.sender_id === userId;
  const sender = message.sender_type === 'ai' ? '✦ AI-ассистент' : message.sender_type === 'operator' ? 'Оператор' : own ? 'Вы' : 'Клиент';
  return <div className={`message-line ${own ? 'outgoing' : ''}`}><article className={`message ${message.sender_type === 'ai' ? 'ai-message' : ''}`}><b>{sender}</b><p>{message.content}</p><small>{formatTime(message.created_at)}{message.confidence ? ` · уверенность ${Math.round(message.confidence * 100)}%` : ''}</small></article></div>;
}

function Composer({ onSend, disabled }) {
  const [value, setValue] = useState('');
  async function submit(event) { event.preventDefault(); if (!value.trim() || disabled) return; const content = value; setValue(''); await onSend(content); }
  return <form className="composer" onSubmit={submit}><textarea value={value} onChange={(event) => setValue(event.target.value)} placeholder="Напишите сообщение…" rows="1" disabled={disabled} /><button className="send" aria-label="Отправить" disabled={!value.trim() || disabled}>↑</button></form>;
}

export function ChatPanel({ conversation, messages, userId, isLoading, isSending, onSend, readOnly = false }) {
  const lastMessageRef = useRef(null);
  useEffect(() => lastMessageRef.current?.scrollIntoView({ behavior: 'smooth' }), [messages, isSending]);
  if (!conversation) return <section className="empty-state"><div>✦</div><h2>Выберите диалог</h2><p>История обращения появится здесь.</p></section>;
  return <section className="chat"><header className="chat-header"><div><p className="eyebrow">ОБРАЩЕНИЕ #{conversation.id}</p><h2>{statusLabels[conversation.status] || conversation.status}</h2></div><span className={`pill ${conversation.status}`}>{statusLabels[conversation.status]}</span></header>
    <div className="messages" aria-busy={isLoading}>{isLoading && <p className="muted">Загружаем сообщения…</p>}{messages.map((message) => <Message key={message.id} message={message} userId={userId} />)}{isSending && <div className="message-line"><div className="typing"><span>✦</span><i /><i /><i /><small>AI-ассистент формулирует ответ</small></div></div>}<div ref={lastMessageRef} /></div>
    {!readOnly && <Composer onSend={onSend} disabled={isSending || conversation.status === 'closed'} />}
  </section>;
}
