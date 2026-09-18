const statusLabels = { open: 'Открыт', pending_ai: 'AI отвечает', waiting_for_user: 'Ждёт клиента', waiting_for_operator: 'Ждёт оператора', escalated: 'Эскалация', closed: 'Закрыт' };
const time = (value) => new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' }).format(new Date(value));

export { statusLabels };

export function ConversationList({ conversations, selectedId, onSelect, onCreate, isCreating }) {
  return <aside className="sidebar"><div className="logo"><span>✦</span> assist<span className="logo-dot">.</span></div>
    <button className="new-chat" onClick={onCreate} disabled={isCreating}>{isCreating ? 'Создаём…' : '＋ Новый диалог'}</button>
    <div className="section-title">ДИАЛОГИ <span>{conversations.length}</span></div>
    <nav className="conversation-list" aria-label="Диалоги">{conversations.map((conversation) => <button key={conversation.id} className={`conversation-row ${conversation.id === selectedId ? 'selected' : ''}`} onClick={() => onSelect(conversation.id)}>
      <i className={`status-dot ${conversation.status}`} /><span><b>Обращение #{conversation.id}</b><small>{statusLabels[conversation.status] || conversation.status}</small></span><time>{time(conversation.updated_at)}</time>
    </button>)}</nav>
  </aside>;
}
