const statusLabels = {
  open: 'Открыт',
  pending_ai: 'AI отвечает',
  waiting_for_user: 'Ждёт клиента',
  waiting_for_operator: 'Ждёт оператора',
  escalated: 'Эскалация',
  closed: 'Закрыт',
};

const time = (value) => {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? ''
    : new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' }).format(date);
};

export { statusLabels };

export function ConversationList({
  conversations = [],
  selectedId,
  onSelect,
  onCreate,
  isCreating = false,
  showCreate = true,
  title = 'ДИАЛОГИ',
}) {
  return (
    <aside className="sidebar">
      <div className="logo"><span>✦</span> assist<span className="logo-dot">.</span></div>

      {showCreate && (
        <button className="new-chat" onClick={onCreate} disabled={isCreating}>
          {isCreating ? 'Создаём…' : '＋ Новый диалог'}
        </button>
      )}

      <div className="section-title">
        <span>{title}</span>
        <b>{conversations.length}</b>
      </div>

      <nav className="conversation-list" aria-label={title}>
        {conversations.map((conversation) => (
          <button
            key={conversation.id}
            type="button"
            className={`conversation-row ${conversation.id === selectedId ? 'selected' : ''}`}
            onClick={() => onSelect?.(conversation.id)}
          >
            <i className={`status-dot ${conversation.status}`} aria-hidden="true" />
            <span className="conversation-copy">
              <b>Обращение #{conversation.id}</b>
              <small>{statusLabels[conversation.status] || conversation.status}</small>
            </span>
            <time>{time(conversation.updated_at)}</time>
          </button>
        ))}
        {!conversations.length && <p className="sidebar-empty">Диалогов пока нет.</p>}
      </nav>
    </aside>
  );
}
