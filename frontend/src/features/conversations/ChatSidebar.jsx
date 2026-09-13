import { useMemo, useState } from 'react';
import { LogOut, MessageSquare, Plus } from 'lucide-react';
import { formatConversationTimestamp } from '../../utils/date';
import StatusBadge from './StatusBadge';

const filters = [
  { id: 'all', label: 'Все' },
  { id: 'open', label: 'Активные' },
  { id: 'closed', label: 'Закрытые' },
];

export default function ChatSidebar({ activeConversationId, conversations, currentUser, loading, onCreateConversation, onLogout, onSelectConversation }) {
  const [filter, setFilter] = useState('all');
  const [isCreating, setIsCreating] = useState(false);
  const filteredConversations = useMemo(() => conversations.filter((conversation) => {
    if (filter === 'open') return conversation.status !== 'closed';
    if (filter === 'closed') return conversation.status === 'closed';
    return true;
  }), [conversations, filter]);

  const createConversation = async () => {
    setIsCreating(true);
    try {
      await onCreateConversation();
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <button className="new-chat-btn" disabled={isCreating} onClick={createConversation} type="button"><Plus size={18} strokeWidth={2.5} />{isCreating ? 'Создание...' : 'Новый диалог'}</button>
        <div className="filter-bar">
          {filters.map(({ id, label }) => (
            <button className={`filter-btn ${filter === id ? 'active' : ''}`} key={id} onClick={() => setFilter(id)} type="button">
              {label}{id === 'all' ? ` (${conversations.length})` : ''}
            </button>
          ))}
        </div>
      </div>
      <div className="chat-list">
        {loading && !conversations.length ? <p className="sidebar-empty">Загрузка диалогов...</p> : (
          filteredConversations.length ? filteredConversations.map((conversation) => (
            <button
              className={`chat-item ${conversation.id === activeConversationId ? 'active' : ''}`}
              key={conversation.id}
              onClick={() => onSelectConversation(conversation.id)}
              type="button"
            >
              <span className="chat-item-header"><span className="chat-title"><span className={`priority-indicator priority-${conversation.priority || 'medium'}`} />Диалог #{conversation.id}</span><span className="chat-time">{formatConversationTimestamp(conversation.updated_at || conversation.created_at)}</span></span>
              <span className="chat-item-footer"><StatusBadge status={conversation.status} /><span className="chat-channel">{conversation.channel || 'web'}</span></span>
            </button>
          )) : <EmptySidebar conversationsCount={conversations.length} />
        )}
      </div>
      <footer className="sidebar-footer">
        <div className="user-profile-info">
          <div className="avatar-circle">{(currentUser?.nickname || currentUser?.email || 'U')[0].toUpperCase()}</div>
          <div className="user-meta"><span className="user-name" title={currentUser?.email}>{currentUser?.nickname || currentUser?.email}</span><span className="user-role-badge">{currentUser?.role || 'Пользователь'}</span></div>
        </div>
        <button className="icon-button" onClick={onLogout} title="Выйти из аккаунта" type="button"><LogOut size={16} /></button>
      </footer>
    </aside>
  );
}

function EmptySidebar({ conversationsCount }) {
  return <div className="sidebar-empty"><MessageSquare size={32} />{conversationsCount ? 'Нет диалогов, соответствующих фильтру.' : 'У вас пока нет диалогов. Нажмите «Новый диалог», чтобы начать.'}</div>;
}
